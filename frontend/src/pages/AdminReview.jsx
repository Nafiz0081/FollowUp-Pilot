import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

export default function AdminReview() {
  const { threadId } = useParams();
  const navigate = useNavigate();

  const [interrupt, setInterrupt] = useState(null);
  const [body, setBody] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getMeetingState(threadId)
      .then((result) => {
        if (cancelled) return;
        if (result.done) {
          navigate(`/admin/meetings/${threadId}`, { replace: true });
          return;
        }
        applyInterrupt(result.interrupt);
      })
      .catch((err) => setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  function applyInterrupt(data) {
    setInterrupt(data);
    setBody(data.draft.body);
    setEmail(data.draft.recipient_email);
  }

  async function submitDecision(decision) {
    setSubmitting(true);
    setError("");
    try {
      const result = await api.reviewMeeting(threadId, {
        decision,
        edited_body: body,
        edited_email: email,
      });
      if (result.done) {
        navigate(`/admin/meetings/${threadId}`);
      } else {
        applyInterrupt(result.interrupt);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="page-loading">Loading…</div>;
  if (!interrupt) return null;

  const { draft, attendee_name, is_registered, index, total } = interrupt;

  return (
    <div className="page">
      <div className="card review-card">
        <div className="review-header">
          <h1>Review email {index + 1} of {total}</h1>
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{ width: `${((index + 1) / total) * 100}%` }}
            />
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {!is_registered && (
          <div className="alert alert-warning">
            {attendee_name} isn't a registered user — double-check the email
            address below before sending.
          </div>
        )}

        <label>
          To ({attendee_name})
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>

        <label>
          Subject
          <input value={draft.subject} readOnly />
        </label>

        <label>
          Body
          <textarea
            rows={14}
            className="notes-textarea"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </label>

        <div className="form-actions">
          <button
            className="btn btn-danger"
            disabled={submitting}
            onClick={() => submitDecision("reject")}
          >
            Reject
          </button>
          <button
            className="btn btn-primary"
            disabled={submitting}
            onClick={() => submitDecision("approve")}
          >
            {submitting ? "Sending…" : "Approve & Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
