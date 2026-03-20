/**
 * src/api.js
 * ----------
 * Every HTTP call to the backend lives here.
 * Components never call fetch() directly — they use these functions.
 *
 * TOKEN HANDLING
 * The JWT is stored in localStorage under "smarthire_token".
 * apiRequest() reads it and adds the Authorization header automatically.
 */

const BASE = "http://localhost:8000";

/** Read the saved JWT (or null if not logged in). */
function getToken() {
  return localStorage.getItem("smarthire_token");
}

/** Save the JWT after login / register. */
export function saveToken(token) {
  localStorage.setItem("smarthire_token", token);
}

/** Remove the JWT on logout. */
export function clearToken() {
  localStorage.removeItem("smarthire_token");
}

/**
 * Core fetch wrapper.
 * - Adds Content-Type and Authorization headers automatically.
 * - Throws an Error with the server's detail message on non-2xx responses.
 */
async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  // 204 No Content has no body — return null
  if (res.status === 204) return null;

  const data = await res.json();

  if (!res.ok) {
    // FastAPI returns { detail: "..." } for errors
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }

  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function apiRegister({ name, email, password, role }) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password, role }),
  });
}

export async function apiLogin({ email, password }) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiMe() {
  return apiRequest("/auth/me");
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export async function apiGetJobs({ search, location, job_type } = {}) {
  const params = new URLSearchParams();
  if (search)   params.set("search",   search);
  if (location && location !== "All") params.set("location", location);
  if (job_type && job_type !== "All")  params.set("job_type", job_type);
  const qs = params.toString();
  return apiRequest(`/jobs${qs ? "?" + qs : ""}`);
}

export async function apiGetJob(jobId) {
  return apiRequest(`/jobs/${jobId}`);
}

export async function apiCreateJob(data) {
  return apiRequest("/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function apiUpdateJob(jobId, data) {
  return apiRequest(`/jobs/${jobId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function apiDeleteJob(jobId) {
  return apiRequest(`/jobs/${jobId}`, { method: "DELETE" });
}

// ── Applications ──────────────────────────────────────────────────────────────

export async function apiApply(jobId, { resume_text, resume_skills }) {
  return apiRequest(`/applications/${jobId}/apply`, {
    method: "POST",
    body: JSON.stringify({ resume_text, resume_skills }),
  });
}

export async function apiMyApplications() {
  return apiRequest("/applications/mine");
}

export async function apiJobApplicants(jobId) {
  return apiRequest(`/applications/job/${jobId}`);
}

export async function apiSubmitInterview(appId, { answers, scores, violations_count = 0, disqualified = false }) {
  return apiRequest(`/applications/${appId}/interview`, {
    method: "POST",
    body: JSON.stringify({
      answers,
      score_overall:       scores.overall,
      score_relevance:     scores.relevance,
      score_confidence:    scores.confidence,
      score_emotion:       scores.emotion,
      score_communication: scores.communication,
      violations_count,
      disqualified,
    }),
  });
}
