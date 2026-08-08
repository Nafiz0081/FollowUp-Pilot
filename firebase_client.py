"""Firebase Admin SDK access — Firestore is used purely as a backend-trusted
database. Only this module and the MCP server talk to Firestore; the React
frontend never touches it directly, so no Firestore security rules are needed.
"""
import datetime
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials, firestore

import config

_app = None


def _ensure_initialized() -> None:
    global _app
    if _app is not None:
        return
    if not firebase_admin._apps:
        cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
        _app = firebase_admin.initialize_app(cred)
    else:
        _app = firebase_admin.get_app()


def get_db():
    _ensure_initialized()
    return firestore.client()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── Auth ──────────────────────────────────────────────────────────────

def verify_id_token(id_token: str) -> Dict[str, Any]:
    _ensure_initialized()
    decoded = fb_auth.verify_id_token(id_token)
    return {
        "uid": decoded["uid"],
        "email": decoded.get("email", ""),
    }


# ── Users ─────────────────────────────────────────────────────────────

def create_user_profile(uid: str, email: str, name: str) -> None:
    db = get_db()
    db.collection("users").document(uid).set({
        "uid": uid,
        "email": email.strip().lower(),
        "name": name.strip(),
        "createdAt": _now(),
    })


def get_user_profile(uid: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def get_all_users() -> List[Dict[str, Any]]:
    db = get_db()
    return [doc.to_dict() for doc in db.collection("users").stream()]


# ── Meetings ──────────────────────────────────────────────────────────

def create_meeting_doc(meeting_id: str, thread_id: str, notes: str,
                        created_by_uid: str, created_by_email: str) -> None:
    db = get_db()
    db.collection("meetings").document(meeting_id).set({
        "id": meeting_id,
        "threadId": thread_id,
        "notes": notes,
        "status": "in_progress",
        "createdBy": created_by_uid,
        "createdByEmail": created_by_email,
        "createdAt": _now(),
        "summary": "",
        "attendees": [],
        "sentCount": 0,
        "taskCount": 0,
        "skippedCount": 0,
    })


def update_meeting_doc(meeting_id: str, **fields: Any) -> None:
    db = get_db()
    db.collection("meetings").document(meeting_id).update(fields)


def get_meeting(meeting_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    doc = db.collection("meetings").document(meeting_id).get()
    return doc.to_dict() if doc.exists else None


def list_meetings() -> List[Dict[str, Any]]:
    db = get_db()
    docs = db.collection("meetings").order_by(
        "createdAt", direction=firestore.Query.DESCENDING
    ).stream()
    return [doc.to_dict() for doc in docs]


def record_sent_email(meeting_id: str, record: Dict[str, Any]) -> str:
    db = get_db()
    ref = db.collection("meetings").document(meeting_id).collection("emails").document()
    record = {**record, "id": ref.id, "sentAt": _now()}
    ref.set(record)
    return ref.id


def list_sent_emails(meeting_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    docs = db.collection("meetings").document(meeting_id).collection("emails").stream()
    return [doc.to_dict() for doc in docs]


def list_tasks_for_meeting(meeting_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    docs = db.collection("tasks").where("meetingId", "==", meeting_id).stream()
    return [doc.to_dict() for doc in docs]


# ── Tasks ─────────────────────────────────────────────────────────────

def record_task(record: Dict[str, Any]) -> str:
    db = get_db()
    ref = db.collection("tasks").document()
    record = {**record, "id": ref.id, "createdAt": _now(), "status": "open"}
    ref.set(record)
    return ref.id


def get_tasks_for_email(email: str) -> List[Dict[str, Any]]:
    db = get_db()
    docs = db.collection("tasks").where("ownerEmail", "==", email.strip().lower()).stream()
    return [doc.to_dict() for doc in docs]
