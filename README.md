# FollowUp Pilot

Turns raw meeting notes into approved, personalised follow-up emails — one per
attendee, containing only that person's tasks — with a human reviewing and
approving every email before it sends.

- **Agent**: LangGraph StateGraph + Groq (free LLM API) for analysis/drafting
- **Tools**: a custom MCP server that sends real email (Gmail SMTP) and saves
  action items
- **Backend**: FastAPI, hosting the agent and the human-in-the-loop
  interrupt/resume cycle
- **Auth + database**: Firebase Authentication (login/signup) + Firestore
  (users, meetings, sent emails, tasks) — Firestore is only ever touched by
  the backend via a service account, so no security rules need writing
- **Frontend**: React (Vite)

## How it works

1. An **admin** (an email listed in `ADMIN_EMAILS`) logs in and pastes raw
   meeting notes into the app.
2. The agent extracts a summary, attendees, and action items, then matches
   each attendee name to a registered user's email.
3. For each attendee, it drafts a follow-up email. The admin reviews it in
   the browser — **Approve & Send**, edit the body/recipient first, or
   **Reject** — one at a time.
4. Approved emails send for real over Gmail SMTP, and action items are saved
   to Firestore. Registered users can log in and see their own tracked tasks.

## Prerequisites

- Python 3.14+ and [uv](https://docs.astral.sh/uv/) (already used by this repo)
- Node.js 18+ and npm (for the React frontend)
- A Google account (for Gmail SMTP + Firebase)
- A free [Groq](https://console.groq.com) account

## 1. Firebase setup

1. Go to the [Firebase console](https://console.firebase.google.com/) →
   **Add project** → give it a name → you can disable Google Analytics,
   it's not needed.
2. **Enable email/password sign-in**: in the left sidebar, *Build* →
   *Authentication* → *Get started* → *Sign-in method* tab → enable
   **Email/Password**.
3. **Create Firestore**: left sidebar → *Build* → *Firestore Database* →
   *Create database* → start in **production mode** (any region). You do
   **not** need to write any security rules — the React app never talks to
   Firestore directly, only the FastAPI backend does (via a trusted service
   account), so Firestore's default "deny all client access" rules are
   exactly what you want. Leave them as-is.
4. **Generate a backend service account key**: click the gear icon next to
   *Project Overview* → *Project settings* → *Service accounts* tab →
   *Generate new private key*. This downloads a JSON file. Rename it to
   `firebase-service-account.json` and put it in the **project root**
   (same folder as `agent.py`). It's already in `.gitignore` — never commit it.
5. **Register a web app** (for the frontend's Firebase Auth SDK): *Project
   settings* → *General* tab → scroll to *Your apps* → click the `</>` (Web)
   icon → give it a nickname → *Register app* (you don't need Firebase
   Hosting). Copy the `firebaseConfig` values shown — you'll need
   `apiKey`, `authDomain`, `projectId`, and `appId` for `frontend/.env`.

## 2. Groq API key (free LLM)

Go to [console.groq.com/keys](https://console.groq.com/keys), sign up, and
create an API key.

## 3. Gmail App Password (real email sending)

1. Turn on 2-Step Verification on the Gmail account you want to send from:
   [myaccount.google.com/security](https://myaccount.google.com/security).
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
   create an app password for "Mail", and copy the 16-character password.

## 4. Configure environment variables

Copy the values you just collected into **`.env`** in the project root:

```
GROQ_API_KEY=your-groq-key
GROQ_MODEL=llama-3.3-70b-versatile

GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

ADMIN_EMAILS=you@gmail.com

GOOGLE_APPLICATION_CREDENTIALS=./firebase-service-account.json
FRONTEND_ORIGIN=http://localhost:5173
```

`ADMIN_EMAILS` is a comma-separated allowlist — whoever signs up with one of
these emails gets the admin UI (upload meetings, review drafts, see history).
Everyone else just sees their own registration + tracked tasks.

Then copy `frontend/.env.example` to `frontend/.env` and fill in the
`VITE_FIREBASE_*` values from step 1.5, plus `VITE_API_BASE_URL` (defaults to
`http://localhost:8000`, the FastAPI backend).

## 5. Run it

Backend (from the project root):

```
uv sync
uv run main.py
```

This starts FastAPI on `http://localhost:8000` (interactive docs at `/docs`).

Frontend (in a second terminal):

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 6. First run

1. Sign up using the email address you put in `ADMIN_EMAILS` — use your real
   full name, since that's how the agent will recognise you as an attendee.
2. Have other attendees sign up too, using the **exact full name** they're
   referred to by in meeting notes (e.g. "Sarah Chen") — that's how the agent
   matches an extracted attendee name to a real, registered email address.
3. Log in as the admin, go to **Upload meeting**, paste in notes (or use the
   sample notes button), and submit.
4. Review each drafted email — approve, edit, or reject — until the loop
   finishes. Check the recipients' inboxes and **Meeting history** for the
   results.

## Project structure

```
config.py                 env var loading
firebase_client.py        Firestore access (backend-only) + token verification
auth.py                   FastAPI auth dependencies (get_current_user, require_admin)
agent.py                  LangGraph StateGraph: analyze → match attendees → draft →
                           human review (interrupt) → send/save → loop
models.py                 Pydantic schemas for structured LLM output
mcp_server/tools_server.py  MCP server: real Gmail send + Firestore persistence
server.py                 FastAPI app and REST endpoints
main.py                   uvicorn entrypoint
data/checkpoints.db       LangGraph's SQLite checkpoint store (auto-created)
frontend/                 React (Vite) app
```

## Known limitations

- Run the backend as a single process/worker — the SQLite-backed LangGraph
  checkpointer isn't safe across multiple processes.
- Attendee-to-user matching is exact-name (case-insensitive). If notes spell
  a name differently than someone's registered name, they'll be treated as
  unregistered and the admin has to fill in their email manually during review.
