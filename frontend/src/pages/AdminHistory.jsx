import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function AdminHistory() {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listMeetings()
      .then(setMeetings)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <div className="card">
        <h1>Meeting history</h1>
        {loading && <p>Loading…</p>}
        {error && <div className="alert alert-error">{error}</div>}
        {!loading && meetings.length === 0 && (
          <p className="muted">No meetings uploaded yet.</p>
        )}
        {meetings.length > 0 && (
          <table className="meetings-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Summary</th>
                <th>Status</th>
                <th>Sent</th>
                <th>Tasks</th>
                <th>Skipped</th>
              </tr>
            </thead>
            <tbody>
              {meetings.map((m) => (
                <tr key={m.id}>
                  <td>{new Date(m.createdAt).toLocaleString()}</td>
                  <td className="meetings-table-summary">
                    <Link to={`/admin/meetings/${m.id}`}>
                      {m.summary || m.notes?.slice(0, 60) || m.id}
                    </Link>
                  </td>
                  <td>
                    <span className={`status-badge status-${m.status}`}>
                      {m.status}
                    </span>
                  </td>
                  <td>{m.sentCount ?? 0}</td>
                  <td>{m.taskCount ?? 0}</td>
                  <td>{m.skippedCount ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
