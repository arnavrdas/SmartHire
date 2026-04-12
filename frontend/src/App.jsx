import { useState, useEffect, useRef, useCallback } from "react";
import {
  saveToken, clearToken,
  apiRegister, apiLogin, apiMe, apiUpdateProfile,
  apiGetJobs, apiCreateJob, apiUpdateJob,
  apiApply, apiMyApplications, apiJobApplicants,
  apiSubmitInterview, apiAnalyseInterview, apiInterviewDetail,
  apiAdminStats, apiAdminUsers, apiAdminJobs,
} from "./api";

// ─── Question generation (client-side; Phase 2 will use Claude API) ──────────
const AI_QUESTIONS_BANK = {
  "React": ["Explain React's reconciliation algorithm.", "What are the trade-offs of server-side rendering?", "How do you handle state management in large React apps?"],
  "TypeScript": ["How does TypeScript's structural typing work?", "Explain generics with a real-world example.", "What are utility types and when do you use them?"],
  "Python": ["How does Python's GIL affect multithreading?", "Explain generators and their memory advantages.", "What is the difference between __str__ and __repr__?"],
  "NLP": ["How does attention mechanism work in transformers?", "What is the difference between stemming and lemmatization?", "How would you handle class imbalance in NLP classification?"],
  "PyTorch": ["Explain autograd in PyTorch.", "How do you debug a vanishing gradient problem?", "What is the role of DataLoader and how do you optimize it?"],
  "Computer Vision": ["How does a convolutional layer extract features?", "Explain the difference between object detection and segmentation.", "How do you handle overfitting in vision models?"],
  "Product Strategy": ["Walk me through a product decision you've reversed.", "How do you prioritize between user feedback and business goals?", "Describe your approach to defining success metrics for a new feature."],
  "User Research": ["How do you decide when to do qualitative vs quantitative research?", "Describe a time user research changed your product direction.", "What methods do you use to validate problem-solution fit?"],
  "default": ["Tell me about yourself and your career goals.", "What is your greatest professional achievement?", "Where do you see yourself in five years?", "Describe a challenging project and how you overcame obstacles.", "Why are you interested in this role?"]
};

function generateQuestions(skills = []) {
  const questions = [...AI_QUESTIONS_BANK["default"]];
  skills.forEach(skill => {
    const bank = AI_QUESTIONS_BANK[skill];
    if (bank) questions.push(...bank.slice(0, 2));
  });
  return questions.sort(() => Math.random() - 0.5).slice(0, 6);
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  app:        { fontFamily: "'DM Sans', sans-serif", minHeight: "100vh", background: "var(--color-background-tertiary)", color: "var(--color-text-primary)" },
  nav:        { background: "var(--color-background-primary)", borderBottom: "0.5px solid var(--color-border-tertiary)", padding: "0 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", height: 56, position: "sticky", top: 0, zIndex: 100 },
  navLogo:    { fontWeight: 700, fontSize: 18, letterSpacing: "-0.5px", color: "var(--color-text-primary)", display: "flex", alignItems: "center", gap: 8, cursor: "pointer" },
  navDot:     { width: 8, height: 8, borderRadius: "50%", background: "#0EA5E9", display: "inline-block" },
  navActions: { display: "flex", gap: 8, alignItems: "center" },
  btn:        { padding: "7px 16px", borderRadius: 8, border: "0.5px solid var(--color-border-secondary)", background: "transparent", cursor: "pointer", fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", fontFamily: "inherit" },
  btnPrimary: { padding: "8px 18px", borderRadius: 8, border: "none", background: "#0EA5E9", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#fff", fontFamily: "inherit" },
  btnDanger:  { padding: "7px 16px", borderRadius: 8, border: "none", background: "#EF4444", cursor: "pointer", fontSize: 13, fontWeight: 500, color: "#fff", fontFamily: "inherit" },
  card:       { background: "var(--color-background-primary)", borderRadius: 12, border: "0.5px solid #d1d5db", padding: "1.25rem" },
  page:       { maxWidth: 1100, margin: "0 auto", padding: "2rem 1.5rem" },
  grid2:      { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem" },
  h1:         { fontSize: 28, fontWeight: 700, letterSpacing: "-0.5px", margin: "0 0 0.25rem" },
  h2:         { fontSize: 20, fontWeight: 600, margin: "0 0 1rem" },
  h3:         { fontSize: 15, fontWeight: 600, margin: "0 0 0.25rem" },
  label:      { fontSize: 12, color: "var(--color-text-secondary)", fontWeight: 500, marginBottom: 4, display: "block" },
  input:      { width: "100%", padding: "9px 12px", borderRadius: 8, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", fontSize: 14, color: "var(--color-text-primary)", fontFamily: "inherit", boxSizing: "border-box" },
  textarea:   { width: "100%", padding: "9px 12px", borderRadius: 8, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", fontSize: 14, color: "var(--color-text-primary)", fontFamily: "inherit", resize: "vertical", minHeight: 80, boxSizing: "border-box" },
  badge: (c) => ({ fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 20,
    background: c==="green"?"#DCFCE7":c==="blue"?"#DBEAFE":c==="amber"?"#FEF3C7":c==="red"?"#FEE2E2":"#F3F4F6",
    color:      c==="green"?"#166534":c==="blue"?"#1E40AF":c==="amber"?"#92400E":c==="red"?"#991B1B":"#374151" }),
  divider:    { height: 1, background: "var(--color-border-tertiary)", margin: "1.25rem 0" },
  muted:      { color: "var(--color-text-secondary)", fontSize: 13 },
  errorBox:   { fontSize: 12, color: "#EF4444", marginBottom: 12, padding: "8px 12px", background: "#FEE2E2", borderRadius: 6 },
};

// ─── Shared components ────────────────────────────────────────────────────────
function Avatar({ name = "?", size = 36 }) {
  const colors = ["#0EA5E9","#8B5CF6","#EC4899","#10B981","#F59E0B","#EF4444"];
  const color   = colors[(name.charCodeAt(0) || 0) % colors.length];
  const initials= name.split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();
  return <div style={{ width:size, height:size, borderRadius:"50%", background:color, display:"flex", alignItems:"center", justifyContent:"center", fontWeight:700, fontSize:size*0.38, color:"#fff", flexShrink:0 }}>{initials}</div>;
}

function ScoreRing({ score, label, size = 60 }) {
  const color = score >= 75 ? "#10B981" : score >= 55 ? "#F59E0B" : "#EF4444";
  const r = size/2 - 5, circ = 2*Math.PI*r, dash = (score/100)*circ;
  return (
    <div style={{ textAlign:"center" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={4}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={`${dash} ${circ-dash}`} strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`}/>
        <text x={size/2} y={size/2+5} textAnchor="middle" fontSize={size*0.22} fontWeight="700" fill={color}>{score}</text>
      </svg>
      <div style={{ fontSize:11, color:"var(--color-text-secondary)", marginTop:2 }}>{label}</div>
    </div>
  );
}

function SkillTag({ skill }) {
  return <span style={{ fontSize:12, padding:"3px 10px", borderRadius:20, background:"var(--color-background-secondary)", border:"0.5px solid var(--color-border-tertiary)", color:"var(--color-text-secondary)", fontWeight:500 }}>{skill}</span>;
}

function Spinner() {
  return <div style={{ display:"inline-block", width:16, height:16, border:"2px solid var(--color-border-tertiary)", borderTopColor:"#0EA5E9", borderRadius:"50%", animation:"spin 0.7s linear infinite" }} />;
}

// ─── Landing ──────────────────────────────────────────────────────────────────
function Landing({ onLogin, onRegister }) {
  return (
    <div style={{ minHeight:"100vh", background:"var(--color-background-primary)" }}>
      <div style={{ padding:"5rem 2rem 4rem", textAlign:"center", maxWidth:720, margin:"0 auto" }}>
        <div style={{ display:"inline-flex", alignItems:"center", gap:6, background:"#EFF6FF", border:"0.5px solid #BFDBFE", borderRadius:20, padding:"4px 14px", fontSize:12, color:"#1D4ED8", fontWeight:600, marginBottom:24 }}>
          <span>●</span> AI-Powered Interview System
        </div>
        <h1 style={{ fontSize:"clamp(32px,5vw,52px)", fontWeight:800, letterSpacing:"-1.5px", lineHeight:1.1, margin:"0 0 1rem" }}>
          Hire smarter with<br/><span style={{ color:"#0EA5E9" }}>AI-driven interviews</span>
        </h1>
        <p style={{ fontSize:17, color:"var(--color-text-secondary)", lineHeight:1.6, marginBottom:36 }}>
          SmartHire evaluates candidates through speech analysis, facial emotion detection, and NLP scoring — giving recruiters objective, structured insights instantly.
        </p>
        <div style={{ display:"flex", gap:12, justifyContent:"center", flexWrap:"wrap" }}>
          <button style={{ ...S.btnPrimary, fontSize:15, padding:"12px 28px" }} onClick={onRegister}>Get Started Free</button>
          <button style={{ ...S.btn,        fontSize:15, padding:"12px 28px" }} onClick={onLogin}>Sign In</button>
        </div>
      </div>
      <div style={{ display:"flex", gap:16, justifyContent:"center", flexWrap:"wrap", padding:"0 2rem 5rem" }}>
        {["🎙️ Speech Confidence Analysis","😊 Facial Emotion Detection","🧠 NLP Answer Scoring","📊 Structured Reports","⚡ Real-time Processing"].map(f => (
          <div key={f} style={{ display:"flex", alignItems:"center", gap:8, background:"var(--color-background-secondary)", border:"0.5px solid var(--color-border-tertiary)", borderRadius:999, padding:"8px 16px", fontSize:13, fontWeight:500 }}>{f}</div>
        ))}
      </div>
    </div>
  );
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
function AuthForm({ mode, onAuth, onSwitch }) {
  const [form,  setForm]  = useState({ email:"", password:"", name:"", role:"candidate", company:"" });
  const [error, setError] = useState("");
  const [busy,  setBusy]  = useState(false);
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const handle = async () => {
    setError(""); setBusy(true);
    try {
      let data;
      if (mode === "login") {
        data = await apiLogin({ email: form.email, password: form.password });
      } else {
        if (!form.name) { setError("Name is required"); setBusy(false); return; }
        if (form.role === "hr" && !form.company.trim()) { setError("Company name is required for HR accounts"); setBusy(false); return; }
        data = await apiRegister({ name: form.name, email: form.email, password: form.password, role: form.role, company: form.company || null });
      }
      saveToken(data.access_token);
      onAuth(data.user);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center", background:"var(--color-background-tertiary)", padding:"2rem" }}>
      <div style={{ ...S.card, width:"100%", maxWidth:400 }}>
        <div style={{ marginBottom:24 }}>
          <div style={{ fontWeight:700, fontSize:18, display:"flex", alignItems:"center", justifyContent:"center", gap:8, marginBottom:8 }}>
            <span style={S.navDot}/> SmartHire
          </div>
          <div style={{ textAlign:"center", color:"var(--color-text-secondary)", fontSize:14 }}>
            {mode==="login" ? "Sign in to your account" : "Create your account"}
          </div>
        </div>

        {mode === "register" && (
          <div style={{ marginBottom:16 }}>
            <label style={S.label}>Full Name</label>
            <input style={S.input} placeholder="Arnav Das" value={form.name} onChange={set("name")}/>
          </div>
        )}
        <div style={{ marginBottom:16 }}>
          <label style={S.label}>Email</label>
          <input style={S.input} placeholder="you@example.com" value={form.email} onChange={set("email")} type="email"/>
        </div>
        <div style={{ marginBottom:16 }}>
          <label style={S.label}>Password</label>
          <input style={S.input} placeholder="••••••••" type="password" value={form.password} onChange={set("password")}
            onKeyDown={e => e.key === "Enter" && handle()}/>
        </div>
        {mode === "register" && (
          <div style={{ marginBottom:16 }}>
            <label style={S.label}>I am a</label>
            <select style={S.input} value={form.role} onChange={set("role")}>
              <option value="candidate">Candidate</option>
              <option value="hr">HR / Recruiter</option>
            </select>
          </div>
        )}
        {mode === "register" && form.role === "hr" && (
          <div style={{ marginBottom:16 }}>
            <label style={S.label}>Company Name <span style={{ color:"#EF4444" }}>*</span></label>
            <input style={S.input} placeholder="e.g. Acme Corp" value={form.company} onChange={set("company")}/>
          </div>
        )}

        {error && <div style={S.errorBox}>{error}</div>}

        <button style={{ ...S.btnPrimary, width:"100%", padding:11, display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}
          onClick={handle} disabled={busy}>
          {busy && <Spinner/>}
          {mode==="login" ? "Sign In" : "Create Account"}
        </button>

        <div style={{ textAlign:"center", marginTop:16, fontSize:13, color:"var(--color-text-secondary)" }}>
          {mode==="login" ? "Don't have an account? " : "Already have an account? "}
          <span style={{ color:"#0EA5E9", cursor:"pointer", fontWeight:500 }} onClick={onSwitch}>
            {mode==="login" ? "Register" : "Login"}
          </span>
        </div>

        {mode === "login" && (
          <div style={{ marginTop:16, padding:10, background:"var(--color-background-secondary)", borderRadius:8, fontSize:12, color:"var(--color-text-secondary)" }}>
            <strong style={{ color:"var(--color-text-primary)" }}>Demo (run seed.py first):</strong><br/>
            Admin: admin@smarthire.io / admin123<br/>
            HR: hr@smarthire.io / test123<br/>
            Candidate: arnav@candidate.io / test123
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Job Card ─────────────────────────────────────────────────────────────────
function JobCard({ job, onApply, applied, isHR, onEdit, onViewApplicants }) {
  const daysLeft = Math.max(0, Math.ceil((new Date(job.last_date) - new Date()) / 86400000));
  return (
    <div style={S.card}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
        <div>
          <div style={S.h3}>{job.title}</div>
          <div style={{ ...S.muted, fontSize:12 }}>
            {job.hr_company ? <span style={{ fontWeight:600, color:"var(--color-text-primary)" }}>{job.hr_company}</span> : job.hr_name}
            {job.department ? <span> · {job.department}</span> : null}
          </div>
        </div>
        <span style={S.badge(daysLeft < 5 ? "red" : "blue")}>{daysLeft}d left</span>
      </div>
      <div style={{ display:"flex", gap:6, marginBottom:10 }}>
        <span style={S.badge("amber")}>{job.location}</span>
        <span style={S.badge("blue")}>{job.job_type}</span>
      </div>
      <p style={{ fontSize:13, color:"var(--color-text-secondary)", margin:"0 0 10px", lineHeight:1.5 }}>
        {(job.description || "").slice(0,100)}…
      </p>
      <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginBottom:12 }}>
        {(job.skills || []).slice(0,4).map(s => <SkillTag key={s} skill={s}/>)}
        {(job.skills||[]).length > 4 && <SkillTag skill={`+${job.skills.length-4}`}/>}
      </div>
      <div style={{ fontSize:12, color:"var(--color-text-secondary)", marginBottom:12 }}>
        Interview: {job.interview_date ? new Date(job.interview_date).toLocaleDateString("en-IN",{day:"numeric",month:"short"}) : "TBD"}
      </div>
      {isHR ? (
        <div style={{ display:"flex", gap:8 }}>
          <button style={S.btn} onClick={() => onEdit(job)}>Edit</button>
          <button style={S.btnPrimary} onClick={() => onViewApplicants(job)}>
            Applicants ({job.applicant_count ?? 0})
          </button>
        </div>
      ) : (
        <button style={applied ? { ...S.btn, opacity:0.5 } : S.btnPrimary}
          onClick={() => !applied && onApply(job)} disabled={applied}>
          {applied ? "✓ Applied" : "Apply Now"}
        </button>
      )}
    </div>
  );
}

// ─── HR Dashboard ─────────────────────────────────────────────────────────────
function HRDashboard({ user, onCreateJob, onEditJob, onViewApplicants }) {
  const [jobs,    setJobs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  useEffect(() => {
    apiGetJobs()
      .then(all => setJobs(all.filter(j => j.hr_id === user.id)))
      .catch(e  => setError(e.message))
      .finally(() => setLoading(false));
  }, [user.id]);

  const totalApplicants  = jobs.reduce((a,j) => a + (j.applicant_count  || 0), 0);
  const totalShortlisted = jobs.reduce((a,j) => a + (j.shortlisted_count|| 0), 0);

  return (
    <div style={S.page}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:24 }}>
        <div>
          <h1 style={S.h1}>Welcome back, {user.name.split(" ")[0]}</h1>
          <div style={S.muted}>Manage your job openings and review candidates</div>
        </div>
        <button style={S.btnPrimary} onClick={onCreateJob}>+ New Job Opening</button>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))", gap:12, marginBottom:28 }}>
        {[
          { label:"Active Openings",  value: jobs.length },
          { label:"Total Applicants", value: totalApplicants },
          { label:"Shortlisted",      value: totalShortlisted },
        ].map(s => (
          <div key={s.label} style={{ background:"var(--color-background-secondary)", borderRadius:10, padding:"1rem", textAlign:"center" }}>
            <div style={{ fontSize:28, fontWeight:700 }}>{s.value}</div>
            <div style={{ fontSize:12, color:"var(--color-text-secondary)", marginTop:2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      <h2 style={S.h2}>Your Job Openings</h2>
      {loading && <div style={{ color:"var(--color-text-secondary)", display:"flex", gap:8, alignItems:"center" }}><Spinner/> Loading…</div>}
      {error   && <div style={S.errorBox}>{error}</div>}
      {!loading && jobs.length === 0 && (
        <div style={{ ...S.card, textAlign:"center", padding:"3rem", color:"var(--color-text-secondary)" }}>
          No job openings yet. Create your first one!
        </div>
      )}
      <div style={S.grid2}>
        {jobs.map(job => (
          <JobCard key={job.id} job={job} isHR onEdit={onEditJob} onViewApplicants={onViewApplicants}/>
        ))}
      </div>
    </div>
  );
}

// ─── Job Form ─────────────────────────────────────────────────────────────────
function JobForm({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState({
    title: "", department: "", location: "Remote", job_type: "Full-time",
    skills: "", description: "", last_date: "", interview_date: "",
    ...(initial ? { ...initial, skills: (initial.skills||[]).join(", "), job_type: initial.job_type } : {})
  });
  const [error, setError] = useState("");
  const [busy,  setBusy]  = useState(false);
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    if (!form.title) { setError("Title is required"); return; }
    setError(""); setBusy(true);
    const payload = {
      ...form,
      skills: form.skills ? form.skills.split(",").map(s=>s.trim()).filter(Boolean) : [],
    };
    try {
      if (initial) { await apiUpdateJob(initial.id, payload); }
      else         { await apiCreateJob(payload); }
      onSaved();
    } catch(e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={S.page}>
      <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:24 }}>
        <button style={S.btn} onClick={onCancel}>← Back</button>
        <h1 style={{ ...S.h1, margin:0 }}>{initial ? "Edit Job Opening" : "Create Job Opening"}</h1>
      </div>
      <div style={{ ...S.card, maxWidth:640 }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
          <div style={{ gridColumn:"1/-1" }}>
            <label style={S.label}>Job Title</label>
            <input style={S.input} value={form.title} onChange={set("title")} placeholder="e.g. Senior Frontend Engineer"/>
          </div>
          <div>
            <label style={S.label}>Department</label>
            <input style={S.input} value={form.department} onChange={set("department")} placeholder="Engineering"/>
          </div>
          <div>
            <label style={S.label}>Location</label>
            <select style={S.input} value={form.location} onChange={set("location")}>
              <option>Remote</option><option>Hybrid</option><option>Bengaluru</option><option>Mumbai</option><option>Delhi</option>
            </select>
          </div>
          <div>
            <label style={S.label}>Employment Type</label>
            <select style={S.input} value={form.job_type} onChange={set("job_type")}>
              <option>Full-time</option><option>Part-time</option><option>Contract</option><option>Internship</option>
            </select>
          </div>
          <div>
            <label style={S.label}>Last Date to Apply</label>
            <input type="date" style={S.input} value={form.last_date} onChange={set("last_date")}/>
          </div>
          <div>
            <label style={S.label}>Interview Date</label>
            <input type="date" style={S.input} value={form.interview_date} onChange={set("interview_date")}/>
          </div>
          <div style={{ gridColumn:"1/-1" }}>
            <label style={S.label}>Required Skills (comma-separated)</label>
            <input style={S.input} value={form.skills} onChange={set("skills")} placeholder="React, TypeScript, CSS"/>
            <div style={{ fontSize:11, color:"var(--color-text-secondary)", marginTop:4 }}>AI uses these to auto-generate interview questions</div>
          </div>
          <div style={{ gridColumn:"1/-1" }}>
            <label style={S.label}>Job Description</label>
            <textarea style={{ ...S.textarea }} value={form.description} onChange={set("description")} rows={4}/>
          </div>
        </div>
        {error && <div style={S.errorBox}>{error}</div>}
        <div style={{ display:"flex", gap:8 }}>
          <button style={{ ...S.btnPrimary, display:"flex", alignItems:"center", gap:8 }} onClick={save} disabled={busy}>
            {busy && <Spinner/>}{initial ? "Save Changes" : "Create Job Opening"}
          </button>
          <button style={S.btn} onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

// ─── Applicants View ──────────────────────────────────────────────────────────
function ApplicantsView({ job, onBack, onReviewInterview }) {
  const [applicants, setApplicants] = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState("");
  const [tab,        setTab]        = useState("all");

  useEffect(() => {
    apiJobApplicants(job.id)
      .then(setApplicants)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [job.id]);

  const shortlisted = applicants.filter(a => a.status === "shortlisted");
  const list = tab === "shortlisted" ? shortlisted : applicants;

  return (
    <div style={S.page}>
      <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:8 }}>
        <button style={S.btn} onClick={onBack}>← Back</button>
        <h1 style={{ ...S.h1, margin:0 }}>{job.title}</h1>
      </div>
      <div style={{ ...S.muted, marginBottom:20 }}>
        {applicants.length} applicants · {shortlisted.length} shortlisted
      </div>

      <div style={{ display:"flex", gap:4, marginBottom:20, background:"var(--color-background-secondary)", padding:4, borderRadius:8, width:"fit-content" }}>
        {["all","shortlisted"].map(t => (
          <button key={t} style={{ ...S.btn, background: tab===t ? "var(--color-background-primary)" : "transparent", border:"none", padding:"6px 16px", fontWeight: tab===t ? 600 : 400 }} onClick={() => setTab(t)}>
            {t==="all" ? `All (${applicants.length})` : `Shortlisted (${shortlisted.length})`}
          </button>
        ))}
      </div>

      {loading && <div style={{ display:"flex", gap:8, alignItems:"center", color:"var(--color-text-secondary)" }}><Spinner/> Loading…</div>}
      {error   && <div style={S.errorBox}>{error}</div>}

      {!loading && list.length === 0 && (
        <div style={{ ...S.card, textAlign:"center", padding:"3rem", color:"var(--color-text-secondary)" }}>
          No {tab==="shortlisted" ? "shortlisted candidates" : "applicants"} yet.
        </div>
      )}

      <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
        {list.map(a => (
          <div key={a.id} style={S.card}>
            <div style={{ display:"flex", alignItems:"center", gap:12, flexWrap:"wrap" }}>
              <Avatar name={a.candidate_name}/>
              <div style={{ flex:1 }}>
                <div style={{ fontWeight:600 }}>{a.candidate_name}</div>
                <div style={{ fontSize:12, color:"var(--color-text-secondary)" }}>{a.status}</div>
              </div>
              {a.score_overall != null ? (
                <div style={{ display:"flex", gap:12, alignItems:"center", flexWrap:"wrap" }}>
                  <ScoreRing score={Math.round(a.score_overall)}        label="Overall"       size={56}/>
                  <ScoreRing score={Math.round(a.score_relevance)}      label="Relevance"     size={50}/>
                  <ScoreRing score={Math.round(a.score_confidence)}     label="Confidence"    size={50}/>
                  <ScoreRing score={Math.round(a.score_emotion)}        label="Emotion"       size={50}/>
                  <ScoreRing score={Math.round(a.score_communication)}  label="Communication" size={50}/>
                  <span style={S.badge(a.score_overall >= 72 ? "green" : "red")}>
                    {a.score_overall >= 72 ? "Recommend" : "Not Recommend"}
                  </span>
                </div>
              ) : (
                <span style={S.badge("amber")}>Interview Pending</span>
              )}
            </div>
            {(a.resume_skills||[]).length > 0 && (
              <div style={{ marginTop:10, display:"flex", flexWrap:"wrap", gap:4 }}>
                {a.resume_skills.map(s => <SkillTag key={s} skill={s}/>)}
              </div>
            )}
            {["interviewed","shortlisted","disqualified"].includes(a.status) && onReviewInterview && (
              <div style={{ marginTop:10 }}>
                <button style={{ ...S.btn, fontSize:12, padding:"5px 14px" }} onClick={() => onReviewInterview(a.id)}>
                  🔍 View Interview &amp; Feedback
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Candidate Dashboard ──────────────────────────────────────────────────────
function CandidateDashboard({ user, onInterview, onReviewInterview }) {
  const [jobs,         setJobs]         = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [applyingJob,  setApplyingJob]  = useState(null);
  const [search,       setSearch]       = useState("");
  const [locationF,    setLocationF]    = useState("All");
  const [typeF,        setTypeF]        = useState("All");

  const reload = useCallback(() => {
    Promise.all([apiGetJobs(), apiMyApplications()])
      .then(([j, a]) => { setJobs(j); setApplications(a); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const appliedJobIds     = applications.map(a => a.job_id);
  const interviewedJobIds = applications.filter(a => a.status !== "interview_pending").map(a => a.job_id);
  const appByJobId        = Object.fromEntries(applications.map(a => [a.job_id, a]));

  const locations = ["All", ...new Set(jobs.map(j=>j.location))];
  const types     = ["All", ...new Set(jobs.map(j=>j.job_type))];

  const filtered = jobs.filter(j => {
    const term = search.toLowerCase();
    const matchSearch = !search || j.title.toLowerCase().includes(term) || (j.skills||[]).some(s=>s.toLowerCase().includes(term));
    const matchLoc  = locationF==="All" || j.location===locationF;
    const matchType = typeF==="All"     || j.job_type===typeF;
    return matchSearch && matchLoc && matchType;
  });

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Find your next role</h1>
      <div style={{ ...S.muted, marginBottom:24 }}>{jobs.length} open positions · {applications.length} applied</div>

      <div style={{ display:"flex", gap:10, marginBottom:24, flexWrap:"wrap" }}>
        <input style={{ ...S.input, maxWidth:320 }} placeholder="Search by role or skill…" value={search} onChange={e=>setSearch(e.target.value)}/>
        <select style={{ ...S.input, width:140 }} value={locationF} onChange={e=>setLocationF(e.target.value)}>
          {locations.map(l=><option key={l}>{l}</option>)}
        </select>
        <select style={{ ...S.input, width:140 }} value={typeF} onChange={e=>setTypeF(e.target.value)}>
          {types.map(t=><option key={t}>{t}</option>)}
        </select>
      </div>

      {applications.length > 0 && (
        <div style={{ marginBottom:32 }}>
          <h2 style={S.h2}>Your Applications</h2>
          <div style={S.grid2}>
            {jobs.filter(j=>appliedJobIds.includes(j.id)).map(job => {
              const app  = appByJobId[job.id];
              const done = interviewedJobIds.includes(job.id);
              return (
                <div key={job.id} style={S.card}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
                    <div>
                      <div style={S.h3}>{job.title}</div>
                      <div style={{ ...S.muted, fontSize:12 }}>{job.department}</div>
                    </div>
                    <span style={S.badge(done?"green":"amber")}>{done?"✓ Done":"Pending"}</span>
                  </div>
                  <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginBottom:12 }}>
                    {(job.skills||[]).slice(0,3).map(s=><SkillTag key={s} skill={s}/>)}
                  </div>
                  {!done ? (
                    <button style={S.btnPrimary} onClick={() => onInterview(job, app)}>Start AI Interview →</button>
                  ) : (
                    <div style={{ display:"flex", gap:8, alignItems:"center", flexWrap:"wrap" }}>
                      <span style={{ fontSize:13, color:"#10B981", fontWeight:500 }}>✓ Interview completed</span>
                      {onReviewInterview && app && (
                        <button style={{ ...S.btn, fontSize:12, padding:"5px 14px" }} onClick={() => onReviewInterview(app.id)}>
                          View Results &amp; Feedback
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {loading && <div style={{ display:"flex", gap:8, alignItems:"center", color:"var(--color-text-secondary)" }}><Spinner/> Loading jobs…</div>}

      <h2 style={S.h2}>All Openings ({filtered.length})</h2>
      <div style={S.grid2}>
        {filtered.map(job => (
          <JobCard key={job.id} job={job} onApply={j => setApplyingJob(j)} applied={appliedJobIds.includes(job.id)}/>
        ))}
      </div>

      {applyingJob && (
        <ApplyModal
          job={applyingJob}
          onClose={() => setApplyingJob(null)}
          onApplied={() => { setApplyingJob(null); reload(); }}
        />
      )}
    </div>
  );
}

// ─── Apply Modal ──────────────────────────────────────────────────────────────
function ApplyModal({ job, onClose, onApplied }) {
  const [resume, setResume] = useState("");
  const [skills, setSkills] = useState("");
  const [step,   setStep]   = useState(1);
  const [busy,   setBusy]   = useState(false);
  const [error,  setError]  = useState("");

  const submit = async () => {
    setBusy(true); setError("");
    try {
      await apiApply(job.id, {
        resume_text: resume,
        resume_skills: skills.split(",").map(s=>s.trim()).filter(Boolean),
      });
      onApplied();
    } catch(e) {
      setError(e.message);
      setStep(1);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.72)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:1000, padding:"1rem" }}>
      <div style={{ width:"100%", maxWidth:480, maxHeight:"90vh", overflowY:"auto", background:"#ffffff", borderRadius:12, border:"1px solid #e5e7eb", padding:"1.5rem", boxShadow:"0 32px 80px rgba(0,0,0,0.5)", boxSizing:"border-box" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <h2 style={{ fontSize:18, fontWeight:700, color:"#111827", margin:0 }}>Apply — {job.title}</h2>
          <button style={{ background:"none", border:"1px solid #d1d5db", borderRadius:6, padding:"4px 10px", cursor:"pointer", fontSize:14, color:"#374151" }} onClick={onClose}>✕</button>
        </div>
        {step === 1 && (
          <>
            <label style={{ fontSize:12, color:"#6b7280", fontWeight:600, marginBottom:4, display:"block" }}>Your Skills (comma-separated)</label>
            <input style={{ width:"100%", padding:"9px 12px", borderRadius:8, border:"1px solid #d1d5db", background:"#f9fafb", fontSize:14, color:"#111827", fontFamily:"inherit", boxSizing:"border-box", marginBottom:16 }} value={skills} onChange={e=>setSkills(e.target.value)} placeholder="React, JavaScript, Node.js"/>
            <label style={{ fontSize:12, color:"#6b7280", fontWeight:600, marginBottom:4, display:"block" }}>Resume Summary / About You</label>
            <textarea style={{ width:"100%", padding:"9px 12px", borderRadius:8, border:"1px solid #d1d5db", background:"#f9fafb", fontSize:14, color:"#111827", fontFamily:"inherit", resize:"vertical", minHeight:100, boxSizing:"border-box", marginBottom:16 }} value={resume} onChange={e=>setResume(e.target.value)} rows={5} placeholder="Briefly describe your experience…"/>
            <div style={{ marginBottom:16, padding:"10px 12px", background:"#f3f4f6", borderRadius:8, fontSize:13, color:"#374151" }}>
              <strong style={{ color:"#111827" }}>Required Skills:</strong>
              <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginTop:6 }}>
                {(job.skills||[]).map(s=><SkillTag key={s} skill={s}/>)}
              </div>
            </div>
            {error && <div style={{ fontSize:12, color:"#dc2626", marginBottom:12, padding:"8px 12px", background:"#fee2e2", borderRadius:6 }}>{error}</div>}
            <button style={{ ...S.btnPrimary, width:"100%" }} onClick={() => setStep(2)} disabled={!skills}>Continue →</button>
          </>
        )}
        {step === 2 && (
          <div style={{ textAlign:"center" }}>
            <div style={{ fontSize:48, marginBottom:12 }}>✅</div>
            <h3 style={{ fontSize:18, fontWeight:700, color:"#111827", marginBottom:8 }}>Ready to apply!</h3>
            <p style={{ color:"#6b7280", fontSize:13, marginBottom:20 }}>After applying, start the AI interview from your dashboard.</p>
            {error && <div style={{ fontSize:12, color:"#dc2626", marginBottom:12, padding:"8px 12px", background:"#fee2e2", borderRadius:6 }}>{error}</div>}
            <button style={{ ...S.btnPrimary, width:"100%", marginBottom:8, display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}
              onClick={submit} disabled={busy}>
              {busy && <Spinner/>} Confirm Application
            </button>
            <button style={{ background:"none", border:"1px solid #d1d5db", borderRadius:8, padding:"9px 16px", cursor:"pointer", fontSize:13, color:"#374151", width:"100%", fontFamily:"inherit" }} onClick={() => setStep(1)}>Go Back</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── CameraPreview — persistent, never unmounts during interview ───────────────
// Keeping the <video> element in a single component that lives for the entire
// interview session (mounted in App, passed down via prop) fixes the camera bug
// where srcObject was lost between question re-renders.
function CameraPreview({ stream, style = {} }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    if (stream) {
      ref.current.srcObject = stream;
      ref.current.play().catch(() => {});
    } else {
      ref.current.srcObject = null;
    }
  }, [stream]);

  return (
    <video
      ref={ref}
      autoPlay
      muted
      playsInline
      style={{ width:"100%", height:"100%", objectFit:"cover", transform:"scaleX(-1)", display:"block", ...style }}
    />
  );
}

// ─── MIME type helpers ────────────────────────────────────────────────────────
function getSupportedVideoMimeType() {
  const types = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
    "video/mp4",
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "video/webm";
}

function getSupportedAudioMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "audio/webm";
}

// ─── useMediaRecorder — records audio and video on separate tracks ────────────
// Two independent MediaRecorder instances:
//   audioRec: audio-only stream  → smaller file, easier for Whisper to decode
//   videoRec: video+audio stream → used by MediaPipe for emotion analysis
function useMediaRecorder(stream) {
  const audioRecRef  = useRef(null);
  const videoRecRef  = useRef(null);
  const audioChunks  = useRef([]);
  const videoChunks  = useRef([]);

  const start = useCallback(() => {
    if (!stream) return;
    audioChunks.current = [];
    videoChunks.current = [];

    const audioTracks = stream.getAudioTracks();
    const videoTracks = stream.getVideoTracks();

    // Audio-only recorder (for Whisper)
    if (audioTracks.length > 0) {
      try {
        const audioStream = new MediaStream(audioTracks);
        const aRec = new MediaRecorder(audioStream, { mimeType: getSupportedAudioMimeType() });
        aRec.ondataavailable = e => { if (e.data.size > 0) audioChunks.current.push(e.data); };
        aRec.start(1000);
        audioRecRef.current = aRec;
      } catch (e) {
        console.warn("Audio recorder failed to start:", e);
      }
    }

    // Video+audio recorder (for MediaPipe emotion analysis)
    if (videoTracks.length > 0) {
      try {
        const videoStream = new MediaStream([
          ...videoTracks,
          ...audioTracks,
        ]);
        const vRec = new MediaRecorder(videoStream, { mimeType: getSupportedVideoMimeType() });
        vRec.ondataavailable = e => { if (e.data.size > 0) videoChunks.current.push(e.data); };
        vRec.start(1000);
        videoRecRef.current = vRec;
      } catch (e) {
        console.warn("Video recorder failed to start:", e);
      }
    }
  }, [stream]);

  const stop = useCallback(() => {
    return new Promise(resolve => {
      const aRec = audioRecRef.current;
      const vRec = videoRecRef.current;

      let audioDone = !aRec || aRec.state === "inactive";
      let videoDone = !vRec || vRec.state === "inactive";

      const tryResolve = () => {
        if (!audioDone || !videoDone) return;
        const audioBlob = audioChunks.current.length > 0
          ? new Blob(audioChunks.current, { type: getSupportedAudioMimeType() })
          : new Blob(videoChunks.current, { type: getSupportedVideoMimeType() }); // fallback
        const videoBlob = new Blob(videoChunks.current, { type: getSupportedVideoMimeType() });
        resolve({ audioBlob, videoBlob });
      };

      if (audioDone && videoDone) { tryResolve(); return; }

      if (aRec && aRec.state !== "inactive") {
        aRec.onstop = () => { audioDone = true; tryResolve(); };
        aRec.stop();
      }
      if (vRec && vRec.state !== "inactive") {
        vRec.onstop = () => { videoDone = true; tryResolve(); };
        vRec.stop();
      }
    });
  }, []);

  return { start, stop };
}

// ─── useSpeechRecognition — live speech-to-text using the Web Speech API ──────
//
// Improvements over the previous version:
//   1. Deduplication — the Web Speech API fires onresult with ALL results from
//      the beginning of the session each time (not just the new chunk). The old
//      code used event.resultIndex correctly, but the auto-restart on onend
//      reset the session, making resultIndex start at 0 again and causing
//      duplicated text. Fixed by tracking finalised results with a session
//      counter that resets on restart.
//
//   2. Smarter restart — use a short delay before restarting so the browser
//      has time to release the mic, preventing "already started" errors.
//
//   3. Explicit abort on question change — when the parent flips active off/on
//      (question submitted, new question revealed), the old session is aborted
//      cleanly before the new one starts.
//
//   4. No-speech timeout recovery — browsers fire onerror("no-speech") after
//      ~7 seconds of silence. Previously this set supported=false incorrectly.
//      Now it just restarts.
//
//   5. Grammar hint — passing a SpeechGrammarList with common interview words
//      improves recognition of domain terms in Chromium.
//
// Available in: Chrome, Edge, and Chromium-based browsers.
// NOT available in: Firefox, Safari — those users see "Type your answer".
function useSpeechRecognition({ active, onTranscript }) {
  const recognitionRef  = useRef(null);
  const restartTimer    = useRef(null);
  const sessionFinalIdx = useRef(0);   // tracks which results we've already appended
  const activeRef       = useRef(active);

  const [interimText, setInterimText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [supported,   setSupported]   = useState(true);

  // Keep activeRef in sync so closures inside the effect see the latest value
  useEffect(() => { activeRef.current = active; }, [active]);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }

    if (!active) {
      // Stop any running session cleanly
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (_) {}
        recognitionRef.current = null;
      }
      clearTimeout(restartTimer.current);
      setIsListening(false);
      setInterimText("");
      sessionFinalIdx.current = 0;
      return;
    }

    function startSession() {
      const rec = new SpeechRecognition();
      rec.continuous      = true;
      rec.interimResults  = true;
      rec.lang            = "en-US";
      rec.maxAlternatives = 1;

      // ── Grammar hints (Chromium only — ignored elsewhere) ─────────────────
      // Listing domain words improves recognition for technical interview terms.
      if (window.SpeechGrammarList) {
        const terms = [
          "React", "TypeScript", "Python", "JavaScript", "FastAPI", "Node.js",
          "machine learning", "deep learning", "neural network", "transformer",
          "SQL", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes",
          "algorithm", "data structure", "API", "REST", "GraphQL", "WebSocket",
          "product manager", "stakeholder", "sprint", "agile", "scrum",
          "NLP", "computer vision", "PyTorch", "TensorFlow", "scikit-learn",
        ];
        const grammar = "#JSGF V1.0; grammar terms; public <term> = " +
          terms.join(" | ") + ";";
        const list = new window.SpeechGrammarList();
        list.addFromString(grammar, 1);
        rec.grammars = list;
      }

      // ── Reset per-session result counter ──────────────────────────────────
      sessionFinalIdx.current = 0;

      rec.onstart = () => setIsListening(true);

      rec.onend = () => {
        setIsListening(false);
        setInterimText("");
        recognitionRef.current = null;
        // Restart after a short gap so the browser fully releases the mic
        if (activeRef.current) {
          restartTimer.current = setTimeout(startSession, 300);
        }
      };

      rec.onerror = (e) => {
        setIsListening(false);
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
          // User denied mic permission — disable permanently this session
          setSupported(false);
          return;
        }
        // All other errors (no-speech, network, aborted) are recoverable —
        // onend will fire after onerror and trigger the restart.
      };

      rec.onresult = (event) => {
        let interim = "";
        let newFinal = "";

        for (let i = sessionFinalIdx.current; i < event.results.length; i++) {
          const text = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            newFinal += text + " ";
            sessionFinalIdx.current = i + 1;
          } else {
            interim += text;
          }
        }

        setInterimText(interim);
        if (newFinal.trim()) {
          onTranscript(newFinal);
        }
      };

      recognitionRef.current = rec;
      try { rec.start(); } catch (_) {}
    }

    startSession();

    return () => {
      clearTimeout(restartTimer.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (_) {}
        recognitionRef.current = null;
      }
      setIsListening(false);
      setInterimText("");
      sessionFinalIdx.current = 0;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  return { isListening, interimText, supported };
}

// ─── Interview View ───────────────────────────────────────────────────────────
function InterviewView({ job, application, onComplete, onCancel, stream }) {
  const questions   = useRef(generateQuestions(job.skills || []));
  const [stage,     setStage]     = useState("intro");
  const [qIdx,      setQIdx]      = useState(0);
  const [answers,   setAnswers]   = useState([]);
  const [current,   setCurrent]   = useState("");
  const [qState,    setQState]    = useState("hidden");
  const [timeLeft,  setTimeLeft]  = useState(60);
  const [progress,  setProgress]  = useState(0);
  const [analysisMsg, setAnalysisMsg] = useState("Processing speech patterns…");
  const [scores,    setScores]    = useState(null);
  const [busy,      setBusy]      = useState(false);
  const [error,     setError]     = useState("");
  const [violations,   setViolations]   = useState(0);
  const [warningMsg,   setWarningMsg]   = useState("");
  const [disqualified, setDisqualified] = useState(false);
  const MAX_VIOLATIONS = 3;
  const CHECKPOINT_KEY = `smarthire_interview_${application?.id}`;

  const timerRef        = useRef(null);
  const isAwayRef       = useRef(false);
  const warnTimeRef     = useRef(null);
  const submitAnswerRef = useRef(null);
  const violationsRef   = useRef(0);
  const { start: startRecording, stop: stopRecording } = useMediaRecorder(stream);

  // ── Speech recognition: live voice → textarea ──────────────────────────────
  // Active only while the question is revealed and the timer is running.
  // Transcribed words are appended to current so the candidate sees them
  // appear as they speak. They can also type/edit freely alongside speaking.
  const speechActive = stage === "question" && qState === "revealed";
  const { isListening, interimText, supported: speechSupported } = useSpeechRecognition({
    active: speechActive,
    onTranscript: useCallback((text) => {
      setCurrent(prev => prev + text);
    }, []),
  });

  // ── Checkpoint restore ─────────────────────────────────────────────────────
  useEffect(() => {
    try {
      const saved = localStorage.getItem(CHECKPOINT_KEY);
      if (saved) {
        const cp = JSON.parse(saved);
        if (cp.stage === "question" && cp.answers?.length > 0) {
          setAnswers(cp.answers);
          setQIdx(cp.qIdx ?? 0);
          setViolations(cp.violations ?? 0);
          violationsRef.current = cp.violations ?? 0;
          setStage("question");
        }
      }
    } catch (_) {}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveCheckpoint = (currentAnswers, currentQIdx, currentViolations) => {
    try {
      localStorage.setItem(CHECKPOINT_KEY, JSON.stringify({
        stage: "question", answers: currentAnswers,
        qIdx: currentQIdx, violations: currentViolations, savedAt: Date.now(),
      }));
    } catch (_) {}
  };

  const clearCheckpoint = () => {
    try { localStorage.removeItem(CHECKPOINT_KEY); } catch (_) {}
  };

  // ── Anti-cheat ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (stage !== "question") return;

    history.pushState(null, "", window.location.href);
    const onPopState = () => {
      history.pushState(null, "", window.location.href);
      if (qState === "revealed") recordViolation("Browser back button used");
    };
    window.addEventListener("popstate", onPopState);
    const blockCtx = (e) => e.preventDefault();
    document.addEventListener("contextmenu", blockCtx);
    const blockSel = (e) => { if (qState === "revealed") e.preventDefault(); };
    document.addEventListener("selectstart", blockSel);

    const bc = new BroadcastChannel("smarthire_interview");
    bc.onmessage = (ev) => {
      if (ev.data === "ping" && qState === "revealed") { bc.postMessage("pong"); recordViolation("Multiple browser windows detected"); }
      if (ev.data === "pong") recordViolation("Multiple browser windows detected");
    };
    bc.postMessage("ping");

    if (qState !== "revealed") {
      return () => {
        window.removeEventListener("popstate", onPopState);
        document.removeEventListener("contextmenu", blockCtx);
        document.removeEventListener("selectstart", blockSel);
        bc.close();
      };
    }

    function recordViolation(reason) {
      if (isAwayRef.current) return;
      isAwayRef.current = true;
      const next = violationsRef.current + 1;
      violationsRef.current = next;
      setViolations(next);
      clearTimeout(warnTimeRef.current);
      if (next >= MAX_VIOLATIONS) {
        clearInterval(timerRef.current);
        if (document.fullscreenElement) document.exitFullscreen().catch(()=>{});
        setWarningMsg(`🚫 ${reason} — 3 violations reached. Interview terminated.`);
        setDisqualified(true);
        clearCheckpoint();
        submitAnswerRef.current?.("__disqualified__");
        return;
      }
      setWarningMsg(`⚠️ ${reason} — Question forfeited. Violation ${next}/${MAX_VIOLATIONS}.`);
      warnTimeRef.current = setTimeout(() => setWarningMsg(""), 6000);
      submitAnswerRef.current?.();
    }

    const recordReturn = () => { isAwayRef.current = false; };
    const onPaste = (e) => {
      if ((e.clipboardData?.getData("text") || "").length > 200) {
        clearTimeout(warnTimeRef.current);
        setWarningMsg("⚠️ Large paste detected and logged.");
        warnTimeRef.current = setTimeout(() => setWarningMsg(""), 5000);
      }
    };
    document.addEventListener("paste", onPaste);

    let devtoolsOpen = false;
    const devtoolsCheck = setInterval(() => {
      const t = performance.now();
      // eslint-disable-next-line no-console
      console.log("%c", "");
      if (performance.now() - t > 160 && !devtoolsOpen) {
        devtoolsOpen = true;
        clearTimeout(warnTimeRef.current);
        setWarningMsg("⚠️ DevTools detected and logged.");
        warnTimeRef.current = setTimeout(() => setWarningMsg(""), 5000);
      }
    }, 3000);

    const onVisibility = () => {
      if (document.hidden) recordViolation("Tab switch detected");
      else                 recordReturn();
    };
    const onBlur  = () => { if (!document.hidden) recordViolation("Window minimized or focus lost"); };
    const onFocus = () => { if (!document.hidden) recordReturn(); };
    const onFullscreenChange = () => {
      if (!document.fullscreenElement) { recordViolation("Exited fullscreen view"); isAwayRef.current = false; }
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur",  onBlur);
    window.addEventListener("focus", onFocus);
    document.addEventListener("fullscreenchange", onFullscreenChange);

    return () => {
      window.removeEventListener("popstate", onPopState);
      document.removeEventListener("contextmenu", blockCtx);
      document.removeEventListener("selectstart", blockSel);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur",  onBlur);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      clearInterval(devtoolsCheck);
      bc.close();
      isAwayRef.current = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, qState]);

  // ── Timer ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (qState !== "revealed") return;
    setTimeLeft(60);
    timerRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) { clearInterval(timerRef.current); submitAnswer(); return 0; }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qState, qIdx]);

  const revealQuestion = () => {
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
    setQState("revealed");
  };

  const submitAnswer = useCallback((marker) => {
    clearInterval(timerRef.current);
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    setQState("hidden");

    const isDisq = marker === "__disqualified__";
    const a = isDisq ? "[Disqualified — interview terminated]" : (current || "[No answer recorded]");

    const newAnswers = [
      ...answers,
      { question_text: questions.current[qIdx], answer_text: a, question_index: qIdx }
    ];
    setAnswers(newAnswers);
    setCurrent("");
    saveCheckpoint(newAnswers, qIdx + 1, violationsRef.current);

    if (isDisq) { finishInterview(newAnswers, true); return; }

    if (qIdx + 1 >= questions.current.length) {
      clearCheckpoint();
      finishInterview(newAnswers, false);
    } else {
      setQIdx(i => i + 1);
      setTimeLeft(60);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, qIdx, answers]);

  useEffect(() => {
    submitAnswerRef.current = submitAnswer;
    violationsRef.current = violations;
  }, [submitAnswer, violations]);

  // ── Start recording when interview begins ──────────────────────────────────
  useEffect(() => {
    if (stage === "question") startRecording();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  // ── Finish — call real AI endpoint ────────────────────────────────────────
  const finishInterview = async (allAnswers, wasDisqualified = false) => {
    setStage("analysis");

    if (wasDisqualified) {
      setScores({ overall:0, relevance:0, confidence:0, emotion:0, communication:0, disqualified:true });
      setStage("result");
      return;
    }

    const msgs = [
      "Processing speech patterns…",
      "Analysing facial expressions…",
      "Scoring answer relevance…",
      "Generating report…",
    ];
    let p = 0;
    const iv = setInterval(() => {
      p = Math.min(p + 4, 90); // advance to 90% while waiting for API
      setProgress(p);
      setAnalysisMsg(msgs[Math.floor(p / 25)] || msgs[3]);
    }, 200);

    try {
      const { audioBlob, videoBlob } = await stopRecording();
      const answerTexts = allAnswers.map(a => a.answer_text);
      const questionTexts = allAnswers.map(a => a.question_text);

      const aiScores = await apiAnalyseInterview({
        audioBlob,
        videoBlob,
        answers:   answerTexts,
        questions: questionTexts,
      });

      clearInterval(iv);
      setProgress(100);
      setScores({ ...aiScores, disqualified: false });
      setTimeout(() => setStage("result"), 400);
    } catch (e) {
      // If AI endpoint fails, fall back to a neutral score rather than crashing
      clearInterval(iv);
      setProgress(100);
      const fallback = { overall:60, relevance:60, confidence:60, emotion:60, communication:60, disqualified:false };
      setScores(fallback);
      setError(`AI analysis unavailable (${e.message}). Scores are estimated.`);
      setTimeout(() => setStage("result"), 400);
    }
  };

  const submitToBackend = async () => {
    if (!scores || !application) return;
    setBusy(true); setError("");
    try {
      await apiSubmitInterview(application.id, {
        answers,
        scores,
        violations_count: violations,
        disqualified: scores.disqualified || false,
      });
      clearCheckpoint();
      onComplete(scores);
    } catch(e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const timerColor = timeLeft > 30 ? "#10B981" : timeLeft > 10 ? "#F59E0B" : "#EF4444";

  // ── INTRO ──────────────────────────────────────────────────────────────────
  if (stage === "intro") return (
    <div style={{ ...S.page, maxWidth: 720 }}>
      <h1 style={S.h1}>AI Interview</h1>
      <div style={{ ...S.muted, marginBottom: 24 }}>{job.title} · {questions.current.length} questions</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div style={S.card}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Camera Preview</div>
          <div style={{ background: "#000", borderRadius: 8, overflow: "hidden", aspectRatio: "4/3", position:"relative" }}>
            {stream
              ? <CameraPreview stream={stream} />
              : <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", color:"#9ca3af", fontSize:13 }}>Camera unavailable</div>
            }
          </div>
          {!stream && (
            <div style={{ marginTop:8, fontSize:12, color:"#F59E0B" }}>
              ⚠ Camera access denied — emotion analysis will use neutral scores.
            </div>
          )}
        </div>
        <div style={S.card}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Instructions</div>
          {[
            "Each question is hidden until you're ready.",
            "Click \"Show Question\" to reveal it — the page enters fullscreen and the 60-second timer starts.",
            "Once shown, the timer cannot be paused.",
            "Type your answer within 60 seconds.",
            "Exiting fullscreen, switching tabs, or minimizing the window counts as a violation.",
            "Your audio and video are recorded for AI analysis.",
          ].map((t, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, fontSize: 13, alignItems: "flex-start" }}>
              <span style={{ color: "#0EA5E9", fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
              <span style={{ lineHeight: 1.4 }}>{t}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ padding: "12px 16px", background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 8, marginBottom: 20, fontSize: 13, color: "#92400E" }}>
        <strong>Integrity Notice:</strong> This interview is monitored. Exiting fullscreen, switching tabs, and minimizing the window are all logged as violations. Your audio and video are recorded for AI analysis only.
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button style={S.btnPrimary} onClick={() => setStage("question")}>Begin Interview →</button>
        <button style={S.btn} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );

  // ── QUESTION ───────────────────────────────────────────────────────────────
  if (stage === "question") {
    const pct = (qIdx / questions.current.length) * 100;
    const revealed = qState === "revealed";
    const ringR = 26, ringCirc = 2 * Math.PI * ringR;
    const ringDash = (timeLeft / 60) * ringCirc;

    return (
      <>
      <style>{`
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
        :fullscreen { background:#f9fafb !important; color:#111827 !important; }
        :-webkit-full-screen { background:#f9fafb !important; color:#111827 !important; }
        ::backdrop { background:#f9fafb !important; }
      `}</style>
      <div style={{ ...S.page, maxWidth: 900, background:"#f9fafb", minHeight:"100vh" }}>
        {warningMsg && (
          <div style={{ position: "fixed", top: 64, left: "50%", transform: "translateX(-50%)", zIndex: 9999, background: "#EF4444", color: "#fff", padding: "12px 24px", borderRadius: 8, fontWeight: 600, fontSize: 14, boxShadow: "0 4px 20px rgba(0,0,0,0.25)", maxWidth: 560, textAlign: "center" }}>
            {warningMsg}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h2 style={{ ...S.h2, margin: 0 }}>Question {qIdx + 1} of {questions.current.length}</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {violations > 0 && (
              <span style={{ fontSize: 12, color: "#EF4444", fontWeight: 600, padding: "2px 10px", background: "#FEE2E2", borderRadius: 20 }}>
                {violations} violation{violations > 1 ? "s" : ""}
              </span>
            )}
            {revealed && (
              <div style={{ position: "relative", width: 64, height: 64 }}>
                <svg width="64" height="64" viewBox="0 0 64 64">
                  <circle cx="32" cy="32" r={ringR} fill="none" stroke="#e5e7eb" strokeWidth={4}/>
                  <circle cx="32" cy="32" r={ringR} fill="none" stroke={timerColor} strokeWidth={4}
                    strokeDasharray={`${ringDash} ${ringCirc - ringDash}`}
                    strokeLinecap="round" transform="rotate(-90 32 32)"
                    style={{ transition: "stroke-dasharray 0.9s linear, stroke 0.3s" }}
                  />
                </svg>
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, fontWeight: 700, color: timerColor }}>
                  {timeLeft}
                </div>
              </div>
            )}
          </div>
        </div>

        <div style={{ height: 4, background: "#e5e7eb", borderRadius: 2, marginBottom: 20 }}>
          <div style={{ height: 4, background: "#0EA5E9", borderRadius: 2, width: `${pct}%`, transition: "width 0.3s" }}/>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 16 }}>
          <div>
            <div style={{ background:"#ffffff", borderRadius:12, border:"1px solid #e5e7eb", padding:"1.25rem", marginBottom: 16, minHeight: 130 }}>
              <div style={{ fontSize: 11, color: "#6b7280", fontWeight: 600, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Question {qIdx + 1}
              </div>
              {!revealed ? (
                <div style={{ textAlign: "center", padding: "16px 0" }}>
                  <div style={{ fontSize: 36, marginBottom: 8 }}>🔒</div>
                  <div style={{ fontSize: 14, color: "#6b7280", marginBottom: 16, lineHeight: 1.5 }}>
                    The question is hidden.<br/>Click below when you're ready to start the 60-second timer.
                  </div>
                  <button style={{ ...S.btnPrimary, fontSize: 14, padding: "10px 24px" }} onClick={revealQuestion}>
                    Show Question →
                  </button>
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.4 }}>
                    {questions.current[qIdx]}
                  </div>
                  <div style={{ color:"#6b7280", fontSize: 12, marginTop: 10 }}>
                    Generated from: {(job.skills || []).slice(0, 3).join(", ")}
                  </div>
                </>
              )}
            </div>

            <div style={{ background:"#ffffff", borderRadius:12, border:"1px solid #e5e7eb", padding:"1.25rem", opacity: revealed ? 1 : 0.45, pointerEvents: revealed ? "auto" : "none" }}>
              {/* Label row: title + live mic indicator */}
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:6 }}>
                <label style={{ fontSize:12, color:"#6b7280", fontWeight:600 }}>Your Answer</label>
                {revealed && (
                  speechSupported
                    ? (
                      <span style={{ display:"flex", alignItems:"center", gap:5, fontSize:11, fontWeight:600,
                          color: isListening ? "#10B981" : "#9ca3af" }}>
                        <span style={{ width:7, height:7, borderRadius:"50%", background: isListening ? "#10B981" : "#d1d5db",
                          animation: isListening ? "pulse 1.2s infinite" : "none", display:"inline-block" }}/>
                        {isListening ? "Listening…" : "Mic ready"}
                      </span>
                    ) : (
                      <span style={{ fontSize:11, color:"#9ca3af" }}>Type your answer (speech not supported in this browser)</span>
                    )
                )}
              </div>

              {/* Textarea — typed text + finalised speech combined */}
              <textarea
                style={{ width:"100%", padding:"9px 12px", borderRadius:8,
                  border: isListening ? "1px solid #10B981" : "1px solid #d1d5db",
                  background:"#f9fafb", fontSize:14, color:"#111827", fontFamily:"inherit",
                  resize:"vertical", minHeight:120, boxSizing:"border-box",
                  marginBottom: interimText ? 4 : 12, transition:"border-color 0.2s" }}
                value={current}
                onChange={e => setCurrent(e.target.value)}
                placeholder={revealed
                  ? (speechSupported ? "Speak or type your answer…" : "Type your answer here…")
                  : "Reveal the question first to begin"}
                disabled={!revealed}
              />

              {/* Interim text: words being spoken right now, not yet finalised */}
              {interimText && (
                <div style={{ fontSize:13, color:"#9ca3af", fontStyle:"italic", marginBottom:10,
                    padding:"4px 8px", background:"#f3f4f6", borderRadius:6, lineHeight:1.4 }}>
                  <span style={{ color:"#10B981", fontWeight:600, fontStyle:"normal" }}>●</span> {interimText}
                </div>
              )}

              {revealed && (
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button style={S.btnDanger} onClick={submitAnswer}>Submit &amp; Next →</button>
                  <span style={{ fontSize: 12, color: "#6b7280" }}>or wait for timer to auto-submit</span>
                </div>
              )}
            </div>
          </div>

          {/* Right column — camera uses CameraPreview, never re-mounts */}
          <div>
            <div style={{ background:"#ffffff", borderRadius:12, border:"1px solid #e5e7eb", padding:"1.25rem", marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Live Camera</div>
              <div style={{ background: "#000", borderRadius: 8, overflow: "hidden", aspectRatio: "4/3", position:"relative" }}>
                {stream
                  ? <CameraPreview stream={stream} />
                  : <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", color:"#9ca3af", fontSize:12 }}>No camera</div>
                }
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
                <span style={{ ...S.badge("green"), display:"flex", alignItems:"center", gap:3 }}>
                  <span style={{ width:6, height:6, borderRadius:"50%", background:"#10B981", animation:"pulse 2s infinite", display:"inline-block" }}/>
                  Recording
                </span>
              </div>
            </div>

            <div style={{ background:"#ffffff", borderRadius:12, border:"1px solid #e5e7eb", padding:"1.25rem" }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "#6b7280" }}>Progress</div>
              {questions.current.map((_, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, fontSize: 12 }}>
                  <div style={{
                    width: 18, height: 18, borderRadius: "50%",
                    background: i < qIdx ? "#10B981" : i === qIdx ? "#0EA5E9" : "#e5e7eb",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 10, color: i <= qIdx ? "#fff" : "#9ca3af"
                  }}>
                    {i < qIdx ? "✓" : i + 1}
                  </div>
                  <span style={{ color: i === qIdx ? "#111827" : "#9ca3af" }}>Q{i + 1}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      </>
    );
  }

  // ── ANALYSIS ───────────────────────────────────────────────────────────────
  if (stage === "analysis") return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", maxWidth: 380 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
        <h2 style={{ ...S.h2, margin: "0 0 8px" }}>Analysing your interview…</h2>
        <p style={S.muted}>AI is evaluating speech, emotions, and answer relevance</p>
        <div style={{ height: 6, background: "var(--color-background-secondary)", borderRadius: 3, margin: "20px 0 8px", overflow: "hidden" }}>
          <div style={{ height: 6, background: "#0EA5E9", borderRadius: 3, width: `${progress}%`, transition: "width 0.2s" }}/>
        </div>
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{analysisMsg}</div>
      </div>
    </div>
  );

  // ── RESULT ─────────────────────────────────────────────────────────────────
  if (stage === "result" && scores) return (
    <div style={{ ...S.page, maxWidth: 680 }}>
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>
          {scores.disqualified ? "🚫" : scores.overall >= 72 ? "🎉" : "📋"}
        </div>
        <h1 style={S.h1}>{scores.disqualified ? "Interview Terminated" : "Interview Complete!"}</h1>
        <p style={S.muted}>{scores.disqualified ? "You were disqualified due to integrity violations." : "Here's your AI performance analysis"}</p>
        {violations > 0 && (
          <div style={{ marginTop: 8, fontSize: 13, color: "#EF4444", fontWeight: 500 }}>
            {violations} integrity violation{violations > 1 ? "s" : ""} recorded.
          </div>
        )}
      </div>

      {scores.disqualified ? (
        <div style={{ ...S.card, marginBottom: 16, background: "#FEF2F2", border: "1px solid #FECACA" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ fontSize: 32 }}>🚫</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "#991B1B" }}>Disqualified — 3 Integrity Violations</div>
              <div style={{ fontSize: 13, color: "#991B1B", opacity: 0.8 }}>Your interview has been terminated. The recruiter has been notified.</div>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ ...S.card, marginBottom: 16, background: scores.overall >= 72 ? "#F0FFF4" : "#FFF7ED", border: `1px solid ${scores.overall >= 72 ? "#BBF7D0" : "#FED7AA"}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ fontSize: 32 }}>{scores.overall >= 72 ? "⭐" : "📝"}</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: scores.overall >= 72 ? "#166534" : "#9A3412" }}>
                {scores.overall >= 72 ? "Strong Candidate — Likely to be Shortlisted!" : "Interview Completed — Under Review"}
              </div>
              <div style={{ fontSize: 13, color: scores.overall >= 72 ? "#166534" : "#9A3412", opacity: 0.8 }}>
                {scores.overall >= 72 ? "Your performance exceeded the shortlisting threshold." : "You may not have met the minimum score. Keep practising!"}
              </div>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 12, marginBottom: 24, justifyItems: "center" }}>
        <ScoreRing score={scores.overall}       label="Overall"       size={72}/>
        <ScoreRing score={scores.relevance}     label="Relevance"     size={64}/>
        <ScoreRing score={scores.confidence}    label="Confidence"    size={64}/>
        <ScoreRing score={scores.emotion}       label="Emotion"       size={64}/>
        <ScoreRing score={scores.communication} label="Communication" size={64}/>
      </div>

      <div style={S.card}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Answer Review</div>
        {answers.map((item, i) => (
          <div key={i} style={{ marginBottom: 14, paddingBottom: 14, borderBottom: i < answers.length - 1 ? "0.5px solid var(--color-border-tertiary)" : "none" }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Q{i + 1}: {item.question_text}</div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", fontStyle: "italic" }}>"{item.answer_text}"</div>
          </div>
        ))}
      </div>

      {error && <div style={{ ...S.errorBox, marginTop: 16 }}>{error}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <button style={{ ...S.btnPrimary, display: "flex", alignItems: "center", gap: 8 }} onClick={submitToBackend} disabled={busy}>
          {busy && <Spinner/>} Save & Return to Dashboard
        </button>
      </div>
    </div>
  );

  return null;
}


// ─── ProfileSettings ─────────────────────────────────────────────────────────
function ProfileSettings({ user, onSaved, onClose }) {
  const [form,  setForm]  = useState({ name: user.name || "", company: user.company || "" });
  const [error, setError] = useState("");
  const [busy,  setBusy]  = useState(false);
  const [saved, setSaved] = useState(false);
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    if (!form.name.trim()) { setError("Name cannot be empty"); return; }
    setBusy(true); setError("");
    try {
      const updated = await apiUpdateProfile({ name: form.name, company: form.company || null });
      setSaved(true);
      setTimeout(() => { onSaved(updated); }, 800);
    } catch(e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.6)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:2000, padding:"1rem" }}>
      <div style={{ ...S.card, width:"100%", maxWidth:420 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <h2 style={{ ...S.h2, margin:0 }}>Edit Profile</h2>
          <button style={{ ...S.btn, padding:"4px 10px" }} onClick={onClose}>✕</button>
        </div>

        <div style={{ marginBottom:16 }}>
          <label style={S.label}>Full Name</label>
          <input style={S.input} value={form.name} onChange={set("name")} placeholder="Your name"/>
        </div>

        {user.role === "hr" && (
          <div style={{ marginBottom:16 }}>
            <label style={S.label}>Company Name</label>
            <input style={S.input} value={form.company} onChange={set("company")} placeholder="e.g. Acme Corp"/>
            <div style={{ fontSize:11, color:"var(--color-text-secondary)", marginTop:4 }}>
              Shown to candidates on all your job postings
            </div>
          </div>
        )}

        <div style={{ marginBottom:16, padding:"10px 12px", background:"var(--color-background-secondary)", borderRadius:8, fontSize:13, color:"var(--color-text-secondary)" }}>
          <div><strong style={{ color:"var(--color-text-primary)" }}>Email:</strong> {user.email}</div>
          <div><strong style={{ color:"var(--color-text-primary)" }}>Role:</strong> {user.role === "hr" ? "HR / Recruiter" : "Candidate"}</div>
          <div style={{ fontSize:11, marginTop:4 }}>Email and role cannot be changed.</div>
        </div>

        {error && <div style={S.errorBox}>{error}</div>}
        {saved && <div style={{ fontSize:13, color:"#10B981", marginBottom:12, padding:"8px 12px", background:"#DCFCE7", borderRadius:6 }}>✓ Profile updated!</div>}

        <div style={{ display:"flex", gap:8 }}>
          <button style={{ ...S.btnPrimary, display:"flex", alignItems:"center", gap:8 }} onClick={save} disabled={busy || saved}>
            {busy && <Spinner/>} Save Changes
          </button>
          <button style={S.btn} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

// ─── InterviewDetailModal ─────────────────────────────────────────────────────
function InterviewDetailModal({ appId, onClose }) {
  const [detail,  setDetail]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  useEffect(() => {
    apiInterviewDetail(appId)
      .then(setDetail)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [appId]);

  const scoreColor = s => s >= 75 ? "#10B981" : s >= 55 ? "#F59E0B" : "#EF4444";
  const labelBadge = l => l === "Excellent" ? "green" : l === "Good" ? "blue" : "red";

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.65)", display:"flex", alignItems:"flex-start", justifyContent:"center", zIndex:2000, padding:"1rem", overflowY:"auto" }}>
      <div style={{ ...S.card, width:"100%", maxWidth:720, margin:"2rem auto", position:"relative" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <h2 style={{ ...S.h2, margin:0 }}>Interview Review</h2>
          <button style={{ ...S.btn, padding:"4px 10px" }} onClick={onClose}>✕</button>
        </div>

        {loading && <div style={{ display:"flex", gap:8, alignItems:"center", color:"var(--color-text-secondary)", padding:"2rem 0" }}><Spinner/> Loading interview data…</div>}
        {error   && <div style={S.errorBox}>{error}</div>}

        {detail && (
          <>
            {/* Status + scores bar */}
            <div style={{ display:"flex", gap:16, marginBottom:20, flexWrap:"wrap", alignItems:"center" }}>
              <span style={S.badge(detail.application.disqualified ? "red" : detail.application.score_overall >= 72 ? "green" : "amber")}>
                {detail.application.disqualified ? "Disqualified" : detail.application.status}
              </span>
              {detail.application.score_overall != null && (
                <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
                  {[
                    ["Overall",       detail.application.score_overall],
                    ["Relevance",     detail.application.score_relevance],
                    ["Confidence",    detail.application.score_confidence],
                    ["Emotion",       detail.application.score_emotion],
                    ["Communication", detail.application.score_communication],
                  ].map(([label, score]) => score != null && (
                    <ScoreRing key={label} score={Math.round(score)} label={label} size={label==="Overall" ? 64 : 52}/>
                  ))}
                </div>
              )}
            </div>

            {/* AI Summary */}
            <div style={{ padding:"14px 16px", background:"#EFF6FF", border:"1px solid #BFDBFE", borderRadius:8, marginBottom:20, fontSize:13, lineHeight:1.6, color:"#1E40AF" }}>
              <div style={{ fontWeight:700, marginBottom:4 }}>🤖 AI Summary</div>
              {detail.summary}
            </div>

            {/* Feedback cards */}
            <h3 style={{ ...S.h3, marginBottom:12 }}>Performance Feedback</h3>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(280px, 1fr))", gap:12, marginBottom:24 }}>
              {detail.feedback.map(fb => (
                <div key={fb.category} style={{ ...S.card, padding:"1rem", border:`1px solid ${scoreColor(fb.score)}22` }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
                    <div style={{ fontWeight:600, fontSize:13 }}>{fb.category}</div>
                    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                      <span style={{ fontWeight:700, fontSize:15, color:scoreColor(fb.score) }}>{fb.score}</span>
                      <span style={S.badge(labelBadge(fb.label))}>{fb.label}</span>
                    </div>
                  </div>
                  {/* Score bar */}
                  <div style={{ height:4, background:"#e5e7eb", borderRadius:2, marginBottom:10 }}>
                    <div style={{ height:4, background:scoreColor(fb.score), borderRadius:2, width:`${fb.score}%`, transition:"width 0.5s" }}/>
                  </div>
                  <div style={{ fontSize:12, color:"var(--color-text-secondary)", lineHeight:1.5 }}>
                    💡 {fb.tip}
                  </div>
                </div>
              ))}
            </div>

            {/* Q&A review */}
            <h3 style={{ ...S.h3, marginBottom:12 }}>Answer Review</h3>
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              {detail.answers.map((a, i) => (
                <div key={i} style={{ ...S.card, padding:"1rem" }}>
                  <div style={{ fontSize:13, fontWeight:600, marginBottom:6, color:"var(--color-text-primary)" }}>
                    Q{i + 1}: {a.question_text}
                  </div>
                  <div style={{ fontSize:13, color:"var(--color-text-secondary)", fontStyle: a.answer_text ? "normal" : "italic", lineHeight:1.5 }}>
                    {a.answer_text && !a.answer_text.startsWith("[")
                      ? `"${a.answer_text}"`
                      : <span style={{ color:"#9CA3AF" }}>{a.answer_text || "No answer recorded"}</span>
                    }
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── AdminPanel ───────────────────────────────────────────────────────────────
function AdminPanel() {
  const [tab,     setTab]     = useState("overview");
  const [stats,   setStats]   = useState(null);
  const [users,   setUsers]   = useState([]);
  const [jobs,    setJobs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  useEffect(() => {
    Promise.all([apiAdminStats(), apiAdminUsers(), apiAdminJobs()])
      .then(([s, u, j]) => { setStats(s); setUsers(u); setJobs(j); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const statCards = stats ? [
    { label:"Total Users",      value: stats.total_users,        color:"#4361ee" },
    { label:"HR / Recruiters",  value: stats.total_hr,           color:"#2d6a4f" },
    { label:"Candidates",       value: stats.total_candidates,   color:"#e63946" },
    { label:"Job Openings",     value: stats.total_jobs,         color:"#f59e0b" },
    { label:"Active Jobs",      value: stats.active_jobs,        color:"#10B981" },
    { label:"Total Applications",value: stats.total_applications,color:"#6c3483" },
    { label:"Shortlisted",      value: stats.shortlisted,        color:"#166534" },
    { label:"Disqualified",     value: stats.disqualified,       color:"#991B1B" },
  ] : [];

  const hrUsers  = users.filter(u => u.role === "hr");
  const candUsers = users.filter(u => u.role === "candidate");

  const tabs = [
    { key:"overview",    label:"Overview" },
    { key:"recruiters",  label:`Recruiters (${hrUsers.length})` },
    { key:"candidates",  label:`Candidates (${candUsers.length})` },
    { key:"jobs",        label:`Jobs (${jobs.length})` },
  ];

  return (
    <div style={S.page}>
      <div style={{ marginBottom:24 }}>
        <h1 style={S.h1}>Admin Panel</h1>
        <div style={S.muted}>Platform overview and management</div>
      </div>

      {loading && <div style={{ display:"flex", gap:8, alignItems:"center", color:"var(--color-text-secondary)" }}><Spinner/> Loading…</div>}
      {error   && <div style={S.errorBox}>{error}</div>}

      {!loading && !error && (
        <>
          {/* Tab bar */}
          <div style={{ display:"flex", gap:4, marginBottom:24, background:"var(--color-background-secondary)", padding:4, borderRadius:8, width:"fit-content" }}>
            {tabs.map(t => (
              <button key={t.key} style={{ ...S.btn, background: tab===t.key ? "var(--color-background-primary)" : "transparent", border:"none", padding:"6px 16px", fontWeight: tab===t.key ? 600 : 400 }} onClick={() => setTab(t.key)}>
                {t.label}
              </button>
            ))}
          </div>

          {/* OVERVIEW */}
          {tab === "overview" && (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(180px, 1fr))", gap:12 }}>
              {statCards.map(s => (
                <div key={s.label} style={{ ...S.card, textAlign:"center", borderTop:`3px solid ${s.color}` }}>
                  <div style={{ fontSize:32, fontWeight:700, color:s.color }}>{s.value}</div>
                  <div style={{ fontSize:12, color:"var(--color-text-secondary)", marginTop:4 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* RECRUITERS */}
          {tab === "recruiters" && (
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              {hrUsers.length === 0 && <div style={{ ...S.card, textAlign:"center", padding:"3rem", color:"var(--color-text-secondary)" }}>No recruiters yet.</div>}
              {hrUsers.map(u => (
                <div key={u.id} style={S.card}>
                  <div style={{ display:"flex", alignItems:"center", gap:12, flexWrap:"wrap" }}>
                    <Avatar name={u.name}/>
                    <div style={{ flex:1 }}>
                      <div style={{ fontWeight:600 }}>{u.name}</div>
                      <div style={{ fontSize:12, color:"var(--color-text-secondary)" }}>{u.email}</div>
                      {u.company && <div style={{ fontSize:12, color:"#4361ee", fontWeight:500 }}>🏢 {u.company}</div>}
                    </div>
                    <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                      <span style={S.badge("blue")}>{u.job_count} jobs</span>
                      <span style={S.muted}>{new Date(u.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* CANDIDATES */}
          {tab === "candidates" && (
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              {candUsers.length === 0 && <div style={{ ...S.card, textAlign:"center", padding:"3rem", color:"var(--color-text-secondary)" }}>No candidates yet.</div>}
              {candUsers.map(u => (
                <div key={u.id} style={S.card}>
                  <div style={{ display:"flex", alignItems:"center", gap:12, flexWrap:"wrap" }}>
                    <Avatar name={u.name}/>
                    <div style={{ flex:1 }}>
                      <div style={{ fontWeight:600 }}>{u.name}</div>
                      <div style={{ fontSize:12, color:"var(--color-text-secondary)" }}>{u.email}</div>
                    </div>
                    <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                      <span style={S.badge("green")}>{u.app_count} applications</span>
                      <span style={S.muted}>{new Date(u.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* JOBS */}
          {tab === "jobs" && (
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              {jobs.length === 0 && <div style={{ ...S.card, textAlign:"center", padding:"3rem", color:"var(--color-text-secondary)" }}>No jobs yet.</div>}
              {jobs.map(j => (
                <div key={j.id} style={{ ...S.card, opacity: j.is_active ? 1 : 0.65 }}>
                  <div style={{ display:"flex", alignItems:"flex-start", gap:12, flexWrap:"wrap" }}>
                    <div style={{ flex:1 }}>
                      <div style={{ fontWeight:600 }}>{j.title}</div>
                      <div style={{ fontSize:12, color:"var(--color-text-secondary)" }}>
                        {j.hr_company || j.hr_name} · {j.department} · {j.location}
                      </div>
                    </div>
                    <div style={{ display:"flex", gap:8, alignItems:"center", flexWrap:"wrap" }}>
                      <span style={S.badge(j.is_active ? "green" : "red")}>{j.is_active ? "Active" : "Closed"}</span>
                      <span style={S.badge("blue")}>{j.applicant_count} applicants</span>
                      <span style={S.badge("amber")}>{j.shortlisted_count} shortlisted</span>
                      <span style={S.muted}>{new Date(j.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [view,         setView]         = useState("landing");
  const [user,         setUser]         = useState(null);
  const [editingJob,   setEditingJob]   = useState(null);
  const [viewingJob,   setViewingJob]   = useState(null);
  const [interviewJob, setInterviewJob] = useState(null);
  const [interviewApp, setInterviewApp] = useState(null);
  const [authChecked,  setAuthChecked]  = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const [cameraError,  setCameraError]  = useState("");
  const [profileOpen,  setProfileOpen]  = useState(false);
  const [reviewAppId,  setReviewAppId]  = useState(null);

  // ── Camera: start when entering interview, stop when leaving ───────────────
  // The stream is owned here (App level) so it survives InterviewView re-renders.
  // CameraPreview receives the stream and attaches it once via a single stable ref.
  useEffect(() => {
    if (view === "interview") {
      setCameraError("");
      navigator.mediaDevices
        .getUserMedia({ video: true, audio: true })
        .then(stream => setCameraStream(stream))
        .catch(err => {
          setCameraStream(null);
          setCameraError(err.name === "NotAllowedError"
            ? "Camera/microphone access denied. Emotion analysis will use neutral scores."
            : `Camera unavailable: ${err.message}`
          );
        });
    } else {
      setCameraStream(prev => {
        if (prev) prev.getTracks().forEach(t => t.stop());
        return null;
      });
    }

    const onUnload = () => {
      setCameraStream(prev => {
        if (prev) prev.getTracks().forEach(t => t.stop());
        return null;
      });
    };
    window.addEventListener("beforeunload", onUnload);
    return () => window.removeEventListener("beforeunload", onUnload);
  }, [view]);

  // ── Session restore ────────────────────────────────────────────────────────
  useEffect(() => {
    const token = localStorage.getItem("smarthire_token");
    if (token) {
      apiMe()
        .then(u => {
          setUser(u);
          if (u.role === "hr") setView("hr-dash");
          else if (u.role === "admin") setView("admin-dash");
          else setView("candidate-dash");
        })
        .catch(() => { clearToken(); })
        .finally(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, []);

  const login  = (u) => {
    setUser(u);
    if (u.role === "hr")        setView("hr-dash");
    else if (u.role === "admin") setView("admin-dash");
    else                         setView("candidate-dash");
  };
  const logout = () => { clearToken(); setUser(null); setView("landing"); };

  const Nav = () => (
    <nav style={S.nav}>
      <div style={S.navLogo} onClick={() => { if (!user) { setView("landing"); return; } if (user.role==="hr") setView("hr-dash"); else if (user.role==="admin") setView("admin-dash"); else setView("candidate-dash"); }}>
        <span style={S.navDot}/> SmartHire
      </div>
      <div style={S.navActions}>
        {user ? (
          <>
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              <Avatar name={user.name} size={28}/>
              <div style={{ display:"flex", flexDirection:"column", lineHeight:1.2 }}>
                <span style={{ fontSize:13, fontWeight:500 }}>{user.name}</span>
                {user.company && <span style={{ fontSize:11, color:"#4361ee" }}>{user.company}</span>}
              </div>
              <span style={S.badge(user.role==="hr"?"blue":user.role==="admin"?"red":"green")}>
                {user.role==="hr"?"HR":user.role==="admin"?"Admin":"Candidate"}
              </span>
            </div>
            {user.role !== "admin" && (
              <button style={S.btn} onClick={() => setProfileOpen(true)}>Edit Profile</button>
            )}
            <button style={S.btn} onClick={logout}>Sign Out</button>
          </>
        ) : (
          <>
            <button style={S.btn}        onClick={() => setView("login")}>Sign In</button>
            <button style={S.btnPrimary} onClick={() => setView("register")}>Register</button>
          </>
        )}
      </div>
    </nav>
  );

  if (!authChecked) return null;

  // ── Global overlays (sit above any view) ────────────────────────────────────
  const Overlays = () => (
    <>
      {profileOpen && (
        <ProfileSettings
          user={user}
          onSaved={(updated) => { setUser(updated); setProfileOpen(false); }}
          onClose={() => setProfileOpen(false)}
        />
      )}
      {reviewAppId && (
        <InterviewDetailModal
          appId={reviewAppId}
          onClose={() => setReviewAppId(null)}
        />
      )}
    </>
  );

  if (view==="landing")  return <div style={S.app}><Nav/><Landing onLogin={() => setView("login")} onRegister={() => setView("register")}/></div>;
  if (view==="login")    return <div style={S.app}><Nav/><AuthForm mode="login"    onAuth={login} onSwitch={() => setView("register")}/></div>;
  if (view==="register") return <div style={S.app}><Nav/><AuthForm mode="register" onAuth={login} onSwitch={() => setView("login")}/></div>;

  if (view==="admin-dash") return (
    <div style={S.app}><Nav/><Overlays/><AdminPanel/></div>
  );

  if (view==="interview") return (
    <div style={S.app}>
      <Nav/>
      <Overlays/>
      {cameraError && (
        <div style={{ background:"#FEF3C7", borderBottom:"1px solid #FDE68A", padding:"8px 2rem", fontSize:12, color:"#92400E" }}>
          ⚠ {cameraError}
        </div>
      )}
      <InterviewView
        job={interviewJob}
        application={interviewApp}
        stream={cameraStream}
        onComplete={() => { setInterviewJob(null); setInterviewApp(null); setView("candidate-dash"); }}
        onCancel={()   => { setInterviewJob(null); setInterviewApp(null); setView("candidate-dash"); }}
      />
    </div>
  );

  if (view==="hr-job-form") return (
    <div style={S.app}>
      <Nav/>
      <Overlays/>
      <JobForm
        initial={editingJob}
        onSaved={() => { setEditingJob(null); setView("hr-dash"); }}
        onCancel={() => { setEditingJob(null); setView("hr-dash"); }}
      />
    </div>
  );

  if (view==="hr-applicants" && viewingJob) return (
    <div style={S.app}>
      <Nav/>
      <Overlays/>
      <ApplicantsView
        job={viewingJob}
        onBack={() => { setViewingJob(null); setView("hr-dash"); }}
        onReviewInterview={(appId) => setReviewAppId(appId)}
      />
    </div>
  );

  if (view==="hr-dash") return (
    <div style={S.app}>
      <Nav/>
      <Overlays/>
      <HRDashboard
        user={user}
        onCreateJob={() => { setEditingJob(null); setView("hr-job-form"); }}
        onEditJob={job => { setEditingJob(job); setView("hr-job-form"); }}
        onViewApplicants={job => { setViewingJob(job); setView("hr-applicants"); }}
      />
    </div>
  );

  if (view==="candidate-dash") return (
    <div style={S.app}>
      <Nav/>
      <Overlays/>
      <CandidateDashboard
        user={user}
        onInterview={(job, app) => { setInterviewJob(job); setInterviewApp(app); setView("interview"); }}
        onReviewInterview={(appId) => setReviewAppId(appId)}
      />
    </div>
  );

  return <div style={S.app}><Nav/><Landing onLogin={() => setView("login")} onRegister={() => setView("register")}/></div>;
}
