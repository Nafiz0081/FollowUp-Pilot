import uuid
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from pydantic import BaseModel

import config
import firebase_client
from agent import build_graph
from auth import get_current_user, require_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = await aiosqlite.connect(config.CHECKPOINT_DB_PATH)
    checkpointer = AsyncSqliteSaver(conn)
    app.state.graph = build_graph().compile(checkpointer=checkpointer)
    try:
        yield
    finally:
        await conn.close()


app = FastAPI(title="FollowUp Pilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/response models ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str


class MeetingCreateRequest(BaseModel):
    notes: str


class ReviewRequest(BaseModel):
    decision: str  # "approve" | "edit" | "reject"
    edited_body: Optional[str] = None
    edited_email: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _result_to_response(meeting_id: str, result: dict) -> dict:
    interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
    if interrupts:
        return {
            "done": False,
            "meeting_id": meeting_id,
            "interrupt": interrupts[0].value,
        }

    sent = result.get("sent_emails", [])
    saved = result.get("saved_tasks", [])
    skipped = result.get("skipped_attendees", [])

    firebase_client.update_meeting_doc(
        meeting_id,
        status="completed",
        summary=result.get("meeting_summary", ""),
        attendees=result.get("attendees", []),
        sentCount=len(sent),
        taskCount=len(saved),
        skippedCount=len(skipped),
    )

    return {
        "done": True,
        "meeting_id": meeting_id,
        "summary": result.get("meeting_summary", ""),
        "sent_count": len(sent),
        "task_count": len(saved),
        "skipped_count": len(skipped),
    }


# ── Auth / users ─────────────────────────────────────────────────────

@app.post("/api/auth/register")
async def register(body: RegisterRequest, user: dict = Depends(get_current_user)):
    firebase_client.create_user_profile(user["uid"], user["email"], body.name)
    return {"status": "ok"}


@app.get("/api/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ── Meetings (admin) ─────────────────────────────────────────────────

@app.post("/api/meetings")
async def create_meeting(body: MeetingCreateRequest, admin: dict = Depends(require_admin)):
    if not body.notes.strip():
        raise HTTPException(400, "Meeting notes cannot be empty")

    meeting_id = uuid.uuid4().hex
    firebase_client.create_meeting_doc(meeting_id, meeting_id, body.notes, admin["uid"], admin["email"])

    result = await app.state.graph.ainvoke(
        {"meeting_id": meeting_id, "meeting_notes": body.notes},
        _thread_config(meeting_id),
    )
    return _result_to_response(meeting_id, result)


@app.get("/api/meetings/{thread_id}/state")
async def get_meeting_state(thread_id: str, admin: dict = Depends(require_admin)):
    snapshot = await app.state.graph.aget_state(_thread_config(thread_id))
    if snapshot.interrupts:
        return {"done": False, "meeting_id": thread_id, "interrupt": snapshot.interrupts[0].value}

    meeting = firebase_client.get_meeting(thread_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return {
        "done": meeting.get("status") == "completed",
        "meeting_id": thread_id,
        "summary": meeting.get("summary", ""),
        "sent_count": meeting.get("sentCount", 0),
        "task_count": meeting.get("taskCount", 0),
        "skipped_count": meeting.get("skippedCount", 0),
    }


@app.post("/api/meetings/{thread_id}/review")
async def review_meeting(thread_id: str, body: ReviewRequest, admin: dict = Depends(require_admin)):
    resume_payload = {
        "decision": body.decision,
        "edited_body": body.edited_body,
        "edited_email": body.edited_email,
    }
    result = await app.state.graph.ainvoke(
        Command(resume=resume_payload), _thread_config(thread_id)
    )
    return _result_to_response(thread_id, result)


@app.get("/api/meetings")
async def list_meetings(admin: dict = Depends(require_admin)):
    return firebase_client.list_meetings()


@app.get("/api/meetings/{meeting_id}/detail")
async def meeting_detail(meeting_id: str, admin: dict = Depends(require_admin)):
    meeting = firebase_client.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return {
        "meeting": meeting,
        "emails": firebase_client.list_sent_emails(meeting_id),
        "tasks": firebase_client.list_tasks_for_meeting(meeting_id),
    }


# ── Regular users ────────────────────────────────────────────────────

@app.get("/api/my-tasks")
async def my_tasks(user: dict = Depends(get_current_user)):
    return firebase_client.get_tasks_for_email(user["email"])
