import { auth } from "./firebase";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch(path, options = {}) {
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError("Not signed in", 401);
  }
  const idToken = await user.getIdToken();

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${idToken}`,
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore — no JSON body
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  me: () => apiFetch("/api/me"),
  register: (name) =>
    apiFetch("/api/auth/register", { method: "POST", body: JSON.stringify({ name }) }),
  createMeeting: (notes) =>
    apiFetch("/api/meetings", { method: "POST", body: JSON.stringify({ notes }) }),
  getMeetingState: (threadId) => apiFetch(`/api/meetings/${threadId}/state`),
  reviewMeeting: (threadId, payload) =>
    apiFetch(`/api/meetings/${threadId}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listMeetings: () => apiFetch("/api/meetings"),
  meetingDetail: (meetingId) => apiFetch(`/api/meetings/${meetingId}/detail`),
  myTasks: () => apiFetch("/api/my-tasks"),
};
