import sys
from pathlib import Path
from typing import Annotated, TypedDict, List, Optional, Dict, Any
import operator

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.constants import END

from langgraph.types import Command, interrupt

from langgraph.graph import StateGraph

import config
import firebase_client
from models import MeetingAnalysis, DraftEmail

# Path to the MCP server script
MCP_SERVER_PATH = Path(__file__).parent / "mcp_server" / "tools_server.py"

MCP_CONFIG = {
    "followup_tools": {
        "command": sys.executable,   # uses the same Python that's running the agent
        "args":    [str(MCP_SERVER_PATH)],
        "transport": "stdio",
    }
}


class AgentState(TypedDict):
    meeting_id: str
    meeting_notes: str
    meeting_summary: str
    attendees: List[str]
    action_items: List[Dict[str, str]]

    # name -> registered email, or None if the attendee isn't a registered user
    attendee_emails: Dict[str, Optional[str]]

    current_attendee_index: int
    current_draft: Optional[Dict[str, Any]]
    review_decision: Optional[str]
    edited_body: Optional[str]
    edited_email: Optional[str]

    sent_emails: Annotated[List[Dict], operator.add]
    saved_tasks: Annotated[List[Dict], operator.add]
    skipped_attendees: Annotated[List[str], operator.add]


ANALYSIS_LLM = ChatGroq(
    model=config.GROQ_MODEL, api_key=config.GROQ_API_KEY
).with_structured_output(MeetingAnalysis)

EMAIL_LLM = ChatGroq(
    model=config.GROQ_MODEL, api_key=config.GROQ_API_KEY, temperature=0.2
).with_structured_output(DraftEmail)


async def analyze_meeting(state: AgentState) -> Dict:
    system = SystemMessage(content=(
        "You are an expert meeting analyst. Extract a concise summary, the "
        "unique full names of every attendee, and every action item "
        "(owner, task, due date) from the raw meeting notes."
    ))
    human = HumanMessage(content=f'Analyze this meeting:\n\n{state["meeting_notes"]}')
    result: MeetingAnalysis = await ANALYSIS_LLM.ainvoke([system, human])

    return {
        'meeting_summary': result.summary,
        'attendees': result.attendees,
        'action_items': [i.model_dump() for i in result.action_items],
        'current_attendee_index': 0,
        'sent_emails': [], 'saved_tasks': [], 'skipped_attendees': [],
    }


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


async def match_attendees(state: AgentState) -> Dict:
    """Match each extracted attendee name to a registered user's email."""
    users = firebase_client.get_all_users()
    by_name = {_normalize_name(u["name"]): u["email"] for u in users if u.get("name")}

    attendee_emails: Dict[str, Optional[str]] = {}
    for attendee in state["attendees"]:
        attendee_emails[attendee] = by_name.get(_normalize_name(attendee))

    return {"attendee_emails": attendee_emails}


async def draft_email(state: AgentState) -> Dict:
    idx = state['current_attendee_index']
    attendee = state['attendees'][idx]
    registered_email = state['attendee_emails'].get(attendee)

    my_tasks = [i for i in state['action_items']
                if i['owner'].lower() == attendee.lower()]

    tasks_text = "\n".join(
        f"  {j+1}. {t['task']} — due {t['due_date']}"
        for j, t in enumerate(my_tasks)
    ) or "  (No specific action items — included as FYI recipient)"

    recipient_hint = (
        f"Their registered email address is exactly: {registered_email}"
        if registered_email
        else "This person is not a registered user — use firstname.lastname@company.com as a placeholder."
    )

    system_msg = SystemMessage(content=(
        "You are a professional executive assistant. "
        "Write concise, warm follow-up emails in plain text only — "
        "no markdown, no bullet symbols. Use numbered lists for action items. "
        "Keep the tone professional but friendly."
    ))

    human_msg = HumanMessage(content=(
        f"Write a follow-up email for {attendee}.\n\n"
        f"Meeting summary: {state['meeting_summary']}\n\n"
        f"Their action items:\n{tasks_text}\n\n"
        f"{recipient_hint}"
    ))

    result: DraftEmail = await EMAIL_LLM.ainvoke([system_msg, human_msg])
    draft = result.model_dump()

    # Never trust the LLM for the actual address if we have a verified one.
    if registered_email:
        draft['recipient_email'] = registered_email

    return {
        'current_draft': {**draft, 'is_registered': bool(registered_email)},
        'review_decision': None,
        'edited_body': None,
        'edited_email': None,
    }


async def human_review(state: AgentState) -> Command:
    payload = interrupt({
        'waiting_for': 'human_review',
        'draft': state['current_draft'],
        'attendee_name': state['attendees'][state['current_attendee_index']],
        'is_registered': state['current_draft'].get('is_registered', False),
        'index': state['current_attendee_index'],
        'total': len(state['attendees']),
    })

    decision = payload.get('decision', 'reject')
    edited_body = payload.get('edited_body')
    edited_email = payload.get('edited_email')

    return Command(update={
        'review_decision': decision,
        'edited_body': edited_body,
        'edited_email': edited_email,
    })


async def execute_action(state: AgentState) -> Dict:
    idx = state['current_attendee_index']
    attendee = state['attendees'][idx]
    draft = state['current_draft']

    if state['review_decision'] == 'reject':
        return {'skipped_attendees': [attendee]}

    email_body = state.get('edited_body') or draft['body']
    recipient_email = state.get('edited_email') or draft['recipient_email']

    my_tasks = [
        item for item in state['action_items']
        if item['owner'].lower() == attendee.lower()
    ]

    sent = []
    saved = []

    client = MultiServerMCPClient(MCP_CONFIG)
    tools = {t.name: t for t in await client.get_tools()}

    send_result = await tools['send_email'].ainvoke({
        'meeting_id': state['meeting_id'],
        'recipient': recipient_email,
        'subject': draft['subject'],
        'body': email_body,
    })

    sent.append({
        'recipient': attendee,
        'email': recipient_email,
        'subject': draft['subject'],
        'result': send_result,
    })

    for task in my_tasks:
        save_result = await tools['save_action_item'].ainvoke({
            'meeting_id': state['meeting_id'],
            'owner': task['owner'],
            'owner_email': recipient_email,
            'task': task['task'],
            'due_date': task['due_date'],
            'meeting_summary': state['meeting_summary'],
        })
        saved.append(save_result)

    return {
        'sent_emails': sent,
        'saved_tasks': saved,
    }


async def advance_attendee(state: AgentState) -> Dict:
    return {'current_attendee_index': state['current_attendee_index'] + 1}


def should_continue(state: AgentState) -> str:
    if state['current_attendee_index'] < len(state['attendees']):
        return 'draft_email'
    return END


def has_attendees(state: AgentState) -> str:
    return 'draft_email' if state['attendees'] else END


def build_graph() -> StateGraph:
    """Uncompiled graph builder. The caller compiles it with a checkpointer."""
    builder = StateGraph(AgentState)

    builder.add_node('analyze_meeting', analyze_meeting)
    builder.add_node('match_attendees', match_attendees)
    builder.add_node('draft_email', draft_email)
    builder.add_node('human_review', human_review)
    builder.add_node('execute_action', execute_action)
    builder.add_node('advance_attendee', advance_attendee)

    builder.set_entry_point('analyze_meeting')
    builder.add_edge('analyze_meeting', 'match_attendees')
    builder.add_conditional_edges(
        'match_attendees',
        has_attendees,
        {'draft_email': 'draft_email', END: END},
    )
    builder.add_edge('draft_email', 'human_review')
    builder.add_edge('human_review', 'execute_action')
    builder.add_edge('execute_action', 'advance_attendee')

    builder.add_conditional_edges(
        'advance_attendee',
        should_continue,
        {'draft_email': 'draft_email', END: END},
    )

    return builder
