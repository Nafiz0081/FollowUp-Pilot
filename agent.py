from typing import Annotated , TypedDict , List , Optional , Dict , Any
import operator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from langgraph.types import Command, interrupt
from models import MeetingAnalysis, DraftEmail


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


