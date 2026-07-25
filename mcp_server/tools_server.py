import datetime

from mcp.server.fastmcp import FastMCP
from pathlib import Path
import json




DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
OUTBOX_FILE = DATA_DIR / 'outbox.json'
TASKS_FILE = DATA_DIR / 'tasks.json'

mcp = FastMCP('FollowUpPilotTools')

def _load_json(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _save_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2, default=str))

@mcp.tool()

def send_email(recipient: str, subject: str, body: str) -> dict:

    """Log an email to the local outbox. Swap body for  real SMTP to ship"""

    outbox = _load_json(OUTBOX_FILE)

    record = {
        'id': f'msg_{len(outbox)+1:04d}',
        'sent_at': datetime.now().isoformat(),
        'recipient': recipient,
        'subject': subject,
        'body': body,
        'status': 'sent',
    }

    outbox.append(record)
    _save_json(OUTBOX_FILE, outbox)
    return {'status': 'ok', 'message_id': record['id']}

@mcp.tool()

def save_action_item(owner:str,task: str, due_date: str, meeting_summary:str)-> dict:

    tasks= _load_json(TASKS_FILE)

    record={
        'id': f'task_{len(tasks)+1:04d}',
        'owner': owner,
        'task': task,
        'due_date': due_date,
        'meeting_summary': meeting_summary,
        'status': 'open',
    }

    tasks.append(record)
    _save_json(TASKS_FILE, tasks)
    return {'status': 'ok', 'task_id': record['id']}

if __name__ == '__main__':
    mcp.run(transport='stdio')

