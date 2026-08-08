import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const SAMPLE_NOTES = `Q3 Product Roadmap Review — attendees: Sarah Chen, Marcus Williams, Priya Patel.

The team aligned on Q3 priorities, elevating mobile checkout to the top of the backlog and deferring push notifications to Q4.

Action items:
- Sarah Chen: update the stakeholder deck with revised timelines, due 2025-07-19.
- Marcus Williams: scope API changes needed for the new checkout flow, due 2025-07-22.
- Marcus Williams: document current API rate limits and share with design, due end of week.
- Priya Patel: deliver high-fidelity mockups for mobile checkout, due 2025-07-25.
- Sarah Chen: note the push notification deferral in the roadmap doc, due 2025-07-22.`;

export default function AdminUpload() {
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const result = await api.createMeeting(notes);
      if (result.done) {
        navigate(`/admin/meetings/${result.meeting_id}`);
      } else {
        navigate(`/admin/review/${result.meeting_id}`);
      }
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h1>Upload meeting minutes</h1>
        <p className="muted">
          Paste raw meeting notes or a transcript. The agent will extract
          attendees and action items, then draft one follow-up email per
          registered attendee for you to review.
        </p>
        <form onSubmit={handleSubmit}>
          {error && <div className="alert alert-error">{error}</div>}
          <textarea
            className="notes-textarea"
            rows={16}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Paste meeting notes here…"
            required
          />
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setNotes(SAMPLE_NOTES)}
            >
              Use sample notes
            </button>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Analyzing…" : "Analyze meeting"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
