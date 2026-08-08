import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";

export default function UserHome() {
  const { profile } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .myTasks()
      .then(setTasks)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <div className="card">
        <h1>Welcome, {profile?.name || "there"}</h1>
        <p>
          You're registered as <strong>{profile?.email}</strong>. When an admin
          uploads meeting minutes that mention you, you'll automatically
          receive a follow-up email with your action items.
        </p>
      </div>

      <div className="card">
        <h2>My tasks</h2>
        {loading && <p>Loading…</p>}
        {error && <div className="alert alert-error">{error}</div>}
        {!loading && tasks.length === 0 && (
          <p className="muted">No tasks tracked for you yet.</p>
        )}
        {tasks.length > 0 && (
          <ul className="task-list">
            {tasks.map((t) => (
              <li key={t.id} className="task-item">
                <div className="task-item-main">{t.task}</div>
                <div className="task-item-meta">
                  Due {t.dueDate} · {t.status}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
