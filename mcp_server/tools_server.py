import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Make the project root importable when this file is spawned as a subprocess
# with a different cwd (MultiServerMCPClient launches it via `sys.executable <path>`).
sys.path.insert(0, str(Path(__file__).parent.parent))

import config  # noqa: E402
import firebase_client  # noqa: E402

mcp = FastMCP('FollowUpPilotTools')


def _send_gmail(recipient: str, subject: str, body: str) -> None:
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD are not set — cannot send real email."
        )

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = config.GMAIL_ADDRESS
    msg['To'] = recipient
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)


@mcp.tool()
def send_email(meeting_id: str, recipient: str, subject: str, body: str) -> dict:
    """Send a real email via Gmail SMTP and log it to Firestore under the meeting."""
    status = 'sent'
    error = None
    try:
        _send_gmail(recipient, subject, body)
    except Exception as exc:  # noqa: BLE001 — surfaced to the caller, not swallowed silently
        status = 'failed'
        error = str(exc)

    doc_id = firebase_client.record_sent_email(meeting_id, {
        'recipient': recipient,
        'subject': subject,
        'body': body,
        'status': status,
        'error': error,
    })

    return {'status': status, 'message_id': doc_id, 'error': error}


@mcp.tool()
def save_action_item(meeting_id: str, owner: str, owner_email: str,
                      task: str, due_date: str, meeting_summary: str) -> dict:
    """Persist an action item for an attendee to Firestore."""
    task_id = firebase_client.record_task({
        'meetingId': meeting_id,
        'owner': owner,
        'ownerEmail': owner_email.strip().lower() if owner_email else '',
        'task': task,
        'dueDate': due_date,
        'meetingSummary': meeting_summary,
    })
    return {'status': 'ok', 'task_id': task_id}


if __name__ == '__main__':
    mcp.run(transport='stdio')
