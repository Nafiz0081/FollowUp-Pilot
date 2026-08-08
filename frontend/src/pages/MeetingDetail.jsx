import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";

export default function MeetingDetail() {
  const { meetingId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .meetingDetail(meetingId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [meetingId]);

  if (loading) return <div className="page-loading">Loading…</div>;
  if (error) return <div className="page"><div className="alert alert-error">{error}</div></div>;

  const { meeting, emails, tasks } = data;

  return (
    <div className="page">
      <div className="card">
        <Link to="/admin/history">&larr; Back to history</Link>
        <h1>{meeting.summary || "Meeting"}</h1>
        <div className="stat-row">
          <div className="stat-tile">
            <div className="stat-value">{meeting.sentCount ?? 0}</div>
            <div className="stat-label">Emails sent</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{meeting.taskCount ?? 0}</div>
            <div className="stat-label">Tasks tracked</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{meeting.skippedCount ?? 0}</div>
            <div className="stat-label">Skipped</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Sent emails</h2>
        {emails.length === 0 && <p className="muted">None sent.</p>}
        {emails.map((e) => (
          <div key={e.id} className="email-record">
            <div className="email-record-header">
              <strong>{e.recipient}</strong>
              <span className={`status-badge status-${e.status}`}>{e.status}</span>
            </div>
            <div className="muted">{e.subject}</div>
            {e.error && <div className="alert alert-error">{e.error}</div>}
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Tasks tracked</h2>
        {tasks.length === 0 && <p className="muted">None.</p>}
        <ul className="task-list">
          {tasks.map((t) => (
            <li key={t.id} className="task-item">
              <div className="task-item-main">
                {t.owner}: {t.task}
              </div>
              <div className="task-item-meta">Due {t.dueDate}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
