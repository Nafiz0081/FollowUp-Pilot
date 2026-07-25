from pydantic import BaseModel, Field
from typing import List



class ActionItem(BaseModel):
    owner: str = Field(description="Full name of the person responsible")
    task : str = Field(description="clear, one-sentence description")
    due_date :str = Field(description="ISO date relative term")


class MeetingAnalysis(BaseModel):
    summary: str = Field(description="2-3 sentence summary.")
    attendees: List[str]= Field(description="Unique Attendee names.")
    action_items : List[ActionItem] = Field(description="All Action items.")


class DraftEmail(BaseModel):
    recipient_name: str = Field(description="Full name.")
    recipient_email: str = Field(description="Inferred email. firstname@company.com if unknow")
    subject:str  = Field (description="Concise Subject Line")
    body: str = Field(description="Plain text body. No markdown")

