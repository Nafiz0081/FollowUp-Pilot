import sys
from pathlib import Path
from typing import Annotated , TypedDict , List , Optional , Dict , Any
import operator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.types import Command, interrupt
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

    meeting_notes: str
    meeting_summary: str
    attendees: List[str]
    action_items: List[Dict[str, str]]
    current_attendee_index: int
    current_draft: Optional[Dict[str, Any]]
    review_decision: Optional[str]
    edited_body: Optional[str]

    sent_emails: Annotated[List[Dict], operator.add]
    saved_tasks: Annotated[List[Dict], operator.add]
    skipped_attendees: Annotated[List[str], operator.add]


ANALYSIS_LLM = ChatAnthropic(model='claude-sonnet-4-5').with_structured_output(MeetingAnalysis)
EMAIL_LLM = ChatAnthropic(model='claude-sonnet-4-5',temperature=0.2).with_structured_output(DraftEmail)
async def analyze_meeting(state: AgentState) -> Dict:

    system = SystemMessage(content= 'You are an expert meeting analyst')
    human = HumanMessage(content =f'Analyze: {state["meeting_notes"]}')
    result : MeetingAnalysis = await ANALYSIS_LLM.invoke([system, human])

    return{
        'meeting_summary': result.summary,
        'attendees': result.attendees,
        'action_items': [i.model_dump() for i in result.action_items],
        'current_attendee_index': 0,
        'sent_emails': [],
        'saved_tasks': [],
        'skipped_attendees': [],
    }


async def draft_email(state: AgentState) -> Dict:

    idx = state['current_attendee_index']
    attendee = state['attendees'][idx]
    my_tasks = [i for i in state['action_items']
               if i['owner'].lower() == attendee.lower()
               ]

    tasks_text = "\n".join(
        f"  {j+1}. {t['task']} — due {t['due_date']}"
        for j, t in enumerate(my_tasks)
    ) or "  (No specific action items — included as FYI recipient)"

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
        "If no email address is available, use firstname.lastname@company.com as a placeholder."
    ))

    result: DraftEmail = await EMAIL_LLM.invoke([system_msg, human_msg])

    return {

        'current_draft' : result.model_dump(),
        'review_decision': None,
        'edited_body': None,

    }

async def human_review(state: AgentState) -> Command

    payload = interrupt({
        'waiting_for': 'human_review',
        'draft': state['current_draft'],
        'attendee_name': state['attendees'][state['current_attendee_index']],
    })

    decision = payload.get('decision','reject')
    edited_body = payload.get('edited_body')

    return Command(update={
        'review_decision': decision,
        'edited_body': edited_body,
    })


async def execute_action(state: AgentState) -> Dict:
    idx      = state['current_attendee_index']
    attendee = state['attendees'][idx]
    draft    = state['current_draft']

    if state['review_decision'] == 'reject':
        return {'skipped_attendees': [attendee]}

    email_body = state.get('edited_body') or draft['body']

    my_tasks = [
        item for item in state['action_items']
        if item['owner'].lower() == attendee.lower()
    ]

    sent  = []
    saved = []

    async with MultiServerMCPClient(MCP_CONFIG) as client:
        tools = {t.name: t for t in client.get_tools()}

        # ── Send the email ─────────────────────────────────────────
        send_result = await tools['send_email'].ainvoke({
            'recipient': draft['recipient_email'],
            'subject':   draft['subject'],
            'body':      email_body,
        })

        sent.append({
            'recipient': attendee,
            'email':     draft['recipient_email'],
            'subject':   draft['subject'],
            'result':    send_result,
        })

        # ── Save each action item for this attendee ────────────────
        for task in my_tasks:
            save_result = await tools['save_action_item'].ainvoke({
                'owner':           task['owner'],
                'task':            task['task'],
                'due_date':        task['due_date'],
                'meeting_summary': state['meeting_summary'],
            })
            saved.append(save_result)

    return {
        'sent_emails': sent,
        'saved_tasks': saved,
    }



