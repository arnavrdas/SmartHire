/**
 * src/api.js
 * ----------
 * Every HTTP call to the backend lives here.
 */

const BASE = "http://localhost:8000";

function getToken() { return localStorage.getItem("smarthire_token"); }
export function saveToken(t) { localStorage.setItem("smarthire_token", t); }
export function clearToken() { localStorage.removeItem("smarthire_token"); }

async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const res  = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) {
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function apiRegister({ name, email, password, role, company }) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password, role, company }),
  });
}

export async function apiLogin({ email, password }) {
  return apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function apiMe() { return apiRequest("/auth/me"); }

export async function apiUpdateProfile({ name, company }) {
  return apiRequest("/auth/profile", {
    method: "PATCH",
    body: JSON.stringify({ name, company }),
  });
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export async function apiGetJobs({ search, location, job_type } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (location && location !== "All") params.set("location", location);
  if (job_type && job_type !== "All")  params.set("job_type", job_type);
  const qs = params.toString();
  return apiRequest(`/jobs${qs ? "?" + qs : ""}`);
}

export async function apiGetJob(jobId)        { return apiRequest(`/jobs/${jobId}`); }
export async function apiCreateJob(data)      { return apiRequest("/jobs", { method: "POST", body: JSON.stringify(data) }); }
export async function apiUpdateJob(jobId, d)  { return apiRequest(`/jobs/${jobId}`, { method: "PUT", body: JSON.stringify(d) }); }
export async function apiDeleteJob(jobId)     { return apiRequest(`/jobs/${jobId}`, { method: "DELETE" }); }

// ── Applications ──────────────────────────────────────────────────────────────

export async function apiApply(jobId, { resume_text, resume_skills }) {
  return apiRequest(`/applications/${jobId}/apply`, {
    method: "POST", body: JSON.stringify({ resume_text, resume_skills }),
  });
}

export async function apiMyApplications()        { return apiRequest("/applications/mine"); }
export async function apiJobApplicants(jobId)    { return apiRequest(`/applications/job/${jobId}`); }

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

export async function apiInterviewDetail(appId) {
  return apiRequest(`/applications/${appId}/detail`);
}

// ── Interview AI Analysis ─────────────────────────────────────────────────────

export async function apiAnalyseInterview({ audioBlob, videoBlob, answers, questions }) {
  const token = getToken();
  const form  = new FormData();
  form.append("audio",     audioBlob, "interview_audio.webm");
  form.append("video",     videoBlob, "interview_video.webm");
  form.append("answers",   JSON.stringify(answers));
  form.append("questions", JSON.stringify(questions));

  const res = await fetch(`${BASE}/interview/analyse`, {
    method:  "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body:    form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function apiAdminStats() { return apiRequest("/admin/stats"); }
export async function apiAdminUsers() { return apiRequest("/admin/users"); }
export async function apiAdminJobs()  { return apiRequest("/admin/jobs"); }