"""
scripts/seed.py
---------------
Populates the database with realistic sample data:
  - 6 HR users
  - 8 candidates
  - 16 job openings across departments
  - 24 applications with completed interviews, scores, and violations

The path fix at the top makes this runnable from EITHER:
  cd backend && python scripts/seed.py
  cd backend/scripts && python seed.py

Safe to run multiple times — existing rows are skipped.
"""

import sys
import os
import random
from datetime import date, timedelta

# ── Path fix ────────────────────────────────────────────────────────────────────
# __file__ is .../backend/scripts/seed.py
# We need .../backend/ on sys.path so that `from db.session import ...` works.
# os.path.dirname(__file__)         → .../backend/scripts   ← wrong
# os.path.dirname(os.path.dirname)  → .../backend           ← correct
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from db.session import SessionLocal
from db.models import User, Job, Application, InterviewAnswer
from core.security import hash_password

db = SessionLocal()
rng = random.Random(42)   # fixed seed → reproducible data every run
today = date.today()


# ── Helpers ───────────────────────────────────────────────────────────────────

def days(n):
    return (today + timedelta(days=n)).isoformat()

def upsert_user(name, email, password, role):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"  skip  user  {email}")
        return existing
    u = User(name=name, email=email, hashed_password=hash_password(password), role=role)
    db.add(u)
    db.flush()
    print(f"  added user  {email}")
    return u


def upsert_job(data):
    existing = db.query(Job).filter(Job.title == data["title"], Job.hr_id == data["hr_id"]).first()
    if existing:
        print(f"  skip  job   '{data['title']}'")
        return existing
    j = Job(**data)
    db.add(j)
    db.flush()
    print(f"  added job   '{data['title']}'")
    return j


def upsert_application(candidate_id, job_id, resume_text, resume_skills,
                       status, scores=None, violations=0, disqualified=False):
    existing = db.query(Application).filter(
        Application.candidate_id == candidate_id,
        Application.job_id == job_id,
    ).first()
    if existing:
        print(f"  skip  application {candidate_id[:8]}… → {job_id[:8]}…")
        return existing
    app = Application(
        candidate_id=candidate_id,
        job_id=job_id,
        resume_text=resume_text,
        resume_skills=resume_skills,
        status=status,
        violations_count=violations,
        disqualified=disqualified,
    )
    if scores:
        app.score_overall       = scores["overall"]
        app.score_relevance     = scores["relevance"]
        app.score_confidence    = scores["confidence"]
        app.score_emotion       = scores["emotion"]
        app.score_communication = scores["communication"]
    db.add(app)
    db.flush()
    print(f"  added application [{status}]")
    return app


def add_answers(application_id, questions_answers):
    """Add interview answers for a completed application."""
    for idx, (q, a) in enumerate(questions_answers):
        db.add(InterviewAnswer(
            application_id=application_id,
            question_text=q,
            answer_text=a,
            question_index=float(idx),
        ))


def rand_scores(bias="mid"):
    """Generate a realistic set of interview scores."""
    ranges = {
        "high":  (75, 97),
        "mid":   (55, 79),
        "low":   (30, 58),
        "zero":  (0, 0),
    }
    lo, hi = ranges[bias]
    r = lambda: round(rng.uniform(lo, hi), 1)
    s = dict(relevance=r(), confidence=r(), emotion=r(), communication=r())
    s["overall"] = round(s["relevance"]*0.35 + s["confidence"]*0.25 +
                         s["emotion"]*0.2 + s["communication"]*0.2, 1)
    return s


# ── Sample answers bank ───────────────────────────────────────────────────────

ANSWER_BANK = {
    "intro": [
        ("Tell me about yourself.", "I'm a software engineer with 4 years of experience building scalable web applications, mostly in React and Python."),
        ("Where do you see yourself in 5 years?", "I'd like to be leading a small engineering team, shipping products that have real user impact."),
        ("What is your greatest achievement?", "Reducing our CI pipeline time by 60% at my last company, which meaningfully improved developer velocity."),
        ("Why are you interested in this role?", "The combination of AI and product work here is exactly where I want to grow my skills."),
    ],
    "React": [
        ("Explain React's reconciliation algorithm.", "React uses a virtual DOM diffing algorithm. It compares trees level by level and minimises real DOM operations."),
        ("What are the trade-offs of server-side rendering?", "SSR improves TTFB and SEO but adds server cost and complexity around data fetching and hydration."),
    ],
    "Python": [
        ("How does Python's GIL affect multithreading?", "The GIL prevents true parallel execution of Python threads, so CPU-bound tasks need multiprocessing instead."),
        ("Explain generators.", "Generators use yield to produce values lazily, keeping only one item in memory at a time."),
    ],
    "NLP": [
        ("How does attention work in transformers?", "Each token computes a query, key, and value. The dot product of query and keys gives attention weights, which scale the values."),
        ("Stemming vs lemmatization?", "Stemming is a crude chop of word suffixes. Lemmatization uses vocabulary and morphological analysis to return the true base form."),
    ],
    "Product Strategy": [
        ("How do you prioritize features?", "I use a combination of impact vs effort scoring, user research, and alignment with quarterly OKRs."),
        ("Tell me about a product decision you reversed.", "We initially built a complex onboarding wizard but data showed 70% drop-off, so we simplified to three steps."),
    ],
    "default": [
        ("Describe a challenging project.", "We migrated a monolith to microservices under a tight deadline. I led the database decomposition and API versioning strategy."),
        ("How do you handle disagreements with colleagues?", "I try to understand their perspective first, then frame my concern around shared goals rather than personal preference."),
    ],
}


def sample_answers(skills):
    """Pick a set of Q&A pairs appropriate for the given skill list."""
    pairs = list(ANSWER_BANK["intro"][:2]) + list(ANSWER_BANK["default"][:1])
    for skill in skills[:3]:
        pairs += ANSWER_BANK.get(skill, [])[:1]
    return pairs[:6]


# ── Seed functions ────────────────────────────────────────────────────────────

def seed_users():
    print("\n── HR Users ──────────────────────────────────")
    hrs = [
        upsert_user("Kuntal Pandya",  "hr@smarthire.io",    "test123", "hr"),
        upsert_user("Rohan Desai",    "hr2@smarthire.io",   "test123", "hr"),
        upsert_user("Meera Iyer",     "meera@smarthire.io", "test123", "hr"),
        upsert_user("Vikram Nair",    "vikram@smarthire.io","test123", "hr"),
        upsert_user("Divya Kapoor",   "divya@smarthire.io", "test123", "hr"),
        upsert_user("Rajan Mehta",    "rajan@smarthire.io", "test123", "hr"),
    ]
    print("\n── Candidate Users ───────────────────────────")
    candidates = [
        upsert_user("Arnav Das",        "arnav@candidate.io",   "test123", "candidate"),
        upsert_user("Priya Sharma",     "priya@candidate.io",   "test123", "candidate"),
        upsert_user("Sahil Gupta",      "sahil@candidate.io",   "test123", "candidate"),
        upsert_user("Ananya Roy",       "ananya@candidate.io",  "test123", "candidate"),
        upsert_user("Karan Malhotra",   "karan@candidate.io",   "test123", "candidate"),
        upsert_user("Nisha Verma",      "nisha@candidate.io",   "test123", "candidate"),
        upsert_user("Dev Patel",        "dev@candidate.io",     "test123", "candidate"),
        upsert_user("Shreya Joshi",     "shreya@candidate.io",  "test123", "candidate"),
    ]
    print("\n── Admin User ───────────────────────────")
    admin = [
        upsert_user("Admin",        "admin@smarthire.io",   "admin123", "admin")
    ]
    db.commit()
    return hrs, candidates


def seed_jobs(hrs):
    kuntal, rohan, meera, vikram, divya, rajan = hrs
    print("\n── Jobs ──────────────────────────────────────")

    jobs_data = [
        # ── Engineering ──────────────────────────────────────────────────────
        dict(title="Senior Frontend Engineer",   department="Engineering",
             location="Remote",    job_type="Full-time",
             description="Own UI architecture across our core product. Deep React and TypeScript required.",
             skills=["React","TypeScript","CSS","Testing","Performance Optimization"],
             last_date=days(30), interview_date="2026-04-20", hr_id=kuntal.id),

        dict(title="Backend Engineer",           department="Engineering",
             location="Remote",    job_type="Full-time",
             description="Build and scale our FastAPI services and data pipeline.",
             skills=["Python","FastAPI","PostgreSQL","Redis","Docker"],
             last_date=days(30), interview_date="2026-04-30", hr_id=kuntal.id),

        dict(title="Full Stack Engineer",        department="Engineering",
             location="Bengaluru", job_type="Full-time",
             description="End-to-end ownership of candidate-facing features.",
             skills=["React","Node.js","PostgreSQL","TypeScript","REST APIs"],
             last_date=days(30), interview_date="2026-05-08", hr_id=meera.id),

        dict(title="DevOps Engineer",            department="Infrastructure",
             location="Remote",    job_type="Full-time",
             description="Manage CI/CD, Kubernetes clusters, and observability stack.",
             skills=["Kubernetes","Docker","Terraform","GitHub Actions","Prometheus"],
             last_date=days(30), interview_date="2026-04-24", hr_id=vikram.id),

        dict(title="iOS Engineer",               department="Engineering",
             location="Hybrid",    job_type="Full-time",
             description="Build our native iOS candidate app from scratch.",
             skills=["Swift","SwiftUI","Combine","CoreData","Xcode"],
             last_date=days(30), interview_date="2026-05-12", hr_id=kuntal.id),

        # ── AI / ML ───────────────────────────────────────────────────────────
        dict(title="ML Engineer",                department="AI & Research",
             location="Bengaluru", job_type="Full-time",
             description="Build and deploy production ML models for our interview analysis pipeline.",
             skills=["Python","PyTorch","NLP","Computer Vision","MLOps"],
             last_date=days(30), interview_date="2026-04-18", hr_id=kuntal.id),

        dict(title="NLP Research Engineer",      department="AI & Research",
             location="Remote",    job_type="Full-time",
             description="Research and ship NLP models for answer relevance scoring.",
             skills=["NLP","Python","HuggingFace","PyTorch","Research"],
             last_date=days(30), interview_date="2026-04-26", hr_id=rohan.id),

        dict(title="Computer Vision Engineer",   department="AI & Research",
             location="Bengaluru", job_type="Full-time",
             description="Build real-time facial emotion detection for live interviews.",
             skills=["Computer Vision","Python","OpenCV","DeepFace","PyTorch"],
             last_date=days(30), interview_date="2026-04-28", hr_id=rohan.id),

        # ── Product ───────────────────────────────────────────────────────────
        dict(title="Product Manager",            department="Product",
             location="Hybrid",    job_type="Full-time",
             description="Lead roadmap for our hiring platform across web and mobile.",
             skills=["Product Strategy","User Research","Agile","Data Analysis","Stakeholder Management"],
             last_date=days(30), interview_date="2026-04-25", hr_id=divya.id),

        dict(title="Senior Product Designer",    department="Design",
             location="Remote",    job_type="Full-time",
             description="Own end-to-end UX for candidate and recruiter experiences.",
             skills=["Figma","User Research","Prototyping","Design Systems","Accessibility"],
             last_date=days(30), interview_date="2026-05-03", hr_id=divya.id),

        dict(title="Product Analyst",            department="Product",
             location="Bengaluru", job_type="Full-time",
             description="Instrument, measure, and improve key product funnels.",
             skills=["SQL","Product Analytics","Amplitude","Python","A/B Testing"],
             last_date=days(30), interview_date="2026-05-09", hr_id=rajan.id),

        # ── Business / GTM ────────────────────────────────────────────────────
        dict(title="Sales Development Rep",      department="Sales",
             location="Mumbai",    job_type="Full-time",
             description="Outbound prospecting and pipeline generation for mid-market accounts.",
             skills=["Sales","CRM","Cold Outreach","Communication","Salesforce"],
             last_date=days(30), interview_date="2026-05-06", hr_id=rajan.id),

        dict(title="Customer Success Manager",   department="Customer Success",
             location="Hybrid",    job_type="Full-time",
             description="Onboard enterprise clients and drive adoption and retention.",
             skills=["Customer Success","SaaS","Onboarding","Data Analysis","Communication"],
             last_date=days(30), interview_date="2026-05-16", hr_id=meera.id),

        dict(title="Marketing Manager",          department="Marketing",
             location="Remote",    job_type="Full-time",
             description="Own demand generation, content, and brand for SmartHire.",
             skills=["Content Marketing","SEO","Analytics","HubSpot","Copywriting"],
             last_date=days(30), interview_date="2026-05-14", hr_id=divya.id),

        # ── Intern / Contract ─────────────────────────────────────────────────
        dict(title="Frontend Intern",            department="Engineering",
             location="Bengaluru", job_type="Internship",
             description="6-month internship working on UI features alongside senior engineers.",
             skills=["React","JavaScript","CSS","HTML","Git"],
             last_date=days(30), interview_date="2026-04-16", hr_id=vikram.id),

        dict(title="Data Analyst Intern",        department="Product",
             location="Remote",    job_type="Internship",
             description="Analyse product usage data and build dashboards for the team.",
             skills=["SQL","Python","Data Visualisation","Excel","Statistics"],
             last_date=days(30), interview_date="2026-04-19", hr_id=rajan.id),
    ]

    jobs = [upsert_job(d) for d in jobs_data]
    db.commit()
    return jobs


def seed_applications(hrs, candidates, jobs):
    kuntal, rohan, meera, vikram, divya, rajan = hrs
    arnav, priya, sahil, ananya, karan, nisha, dev, shreya = candidates

    # Map job title → job object for easy lookup
    by_title = {j.title: j for j in jobs}

    print("\n── Applications ──────────────────────────────")

    apps = [
        # ── High scorers — shortlisted ──────────────────────────────────────
        (arnav,  by_title["Senior Frontend Engineer"],
         "5 years React, led frontend rewrite at Razorpay.",
         ["React","TypeScript","CSS","Testing"],
         "shortlisted", rand_scores("high"), 0, False),

        (arnav,  by_title["Full Stack Engineer"],
         "5 years React, led frontend rewrite at Razorpay.",
         ["React","Node.js","PostgreSQL","TypeScript"],
         "shortlisted", rand_scores("high"), 0, False),

        (priya,  by_title["ML Engineer"],
         "3 years ML engineering at a fintech startup. PyTorch, NLP pipelines.",
         ["Python","PyTorch","NLP","MLOps"],
         "shortlisted", rand_scores("high"), 0, False),

        (priya,  by_title["NLP Research Engineer"],
         "Published NLP research. HuggingFace contributor.",
         ["NLP","Python","HuggingFace","PyTorch"],
         "shortlisted", rand_scores("high"), 1, False),

        (sahil,  by_title["Backend Engineer"],
         "Backend engineer at a Series B startup. Owns auth and data infra.",
         ["Python","FastAPI","PostgreSQL","Redis","Docker"],
         "shortlisted", rand_scores("high"), 0, False),

        (ananya, by_title["Product Manager"],
         "PM at a B2B SaaS company. Grew core metric 40% in 2 quarters.",
         ["Product Strategy","User Research","Agile","Data Analysis"],
         "shortlisted", rand_scores("high"), 0, False),

        (dev,    by_title["NLP Research Engineer"],
         "MSc in Computational Linguistics. Research focus on answer scoring.",
         ["NLP","Python","HuggingFace","PyTorch","Research"],
         "shortlisted", rand_scores("high"), 0, False),

        (shreya, by_title["Senior Product Designer"],
         "5 years UX, led design system at a unicorn startup.",
         ["Figma","User Research","Prototyping","Design Systems"],
         "shortlisted", rand_scores("high"), 0, False),

        # ── Mid scorers — interviewed (under review) ─────────────────────────
        (karan,  by_title["Senior Frontend Engineer"],
         "3 years frontend, mostly Vue. Learning React on the side.",
         ["React","JavaScript","CSS"],
         "interviewed", rand_scores("mid"), 1, False),

        (karan,  by_title["Frontend Intern"],
         "Final year CS student with React projects on GitHub.",
         ["React","JavaScript","CSS","HTML","Git"],
         "interviewed", rand_scores("mid"), 0, False),

        (nisha,  by_title["Backend Engineer"],
         "Django developer at an e-commerce company for 2 years.",
         ["Python","PostgreSQL","Docker"],
         "interviewed", rand_scores("mid"), 0, False),

        (nisha,  by_title["DevOps Engineer"],
         "Infrastructure engineer, some Kubernetes experience.",
         ["Kubernetes","Docker","Terraform"],
         "interviewed", rand_scores("mid"), 2, False),

        (dev,    by_title["Computer Vision Engineer"],
         "MSc thesis on real-time face detection pipelines.",
         ["Computer Vision","Python","OpenCV","PyTorch"],
         "interviewed", rand_scores("mid"), 0, False),

        (sahil,  by_title["Full Stack Engineer"],
         "Backend-heavy but comfortable with React for internal tools.",
         ["Node.js","React","PostgreSQL"],
         "interviewed", rand_scores("mid"), 0, False),

        (ananya, by_title["Product Analyst"],
         "2 years analytics at a consumer app. Strong SQL.",
         ["SQL","Product Analytics","Python","A/B Testing"],
         "interviewed", rand_scores("mid"), 1, False),

        (shreya, by_title["Marketing Manager"],
         "Content lead at a startup. Owns blog and SEO.",
         ["Content Marketing","SEO","HubSpot","Copywriting"],
         "interviewed", rand_scores("mid"), 0, False),

        # ── Low scorers — interviewed (poor performance) ─────────────────────
        (karan,  by_title["ML Engineer"],
         "Interested in ML. Have taken two online courses.",
         ["Python"],
         "interviewed", rand_scores("low"), 0, False),

        (arnav,  by_title["Sales Development Rep"],
         "Applying for a change of domain.",
         ["Communication"],
         "interviewed", rand_scores("low"), 2, False),

        # ── Disqualified ─────────────────────────────────────────────────────
        (nisha,  by_title["NLP Research Engineer"],
         "Applied but violated integrity rules during interview.",
         ["Python","NLP"],
         "disqualified", rand_scores("zero"), 3, True),

        (karan,  by_title["DevOps Engineer"],
         "Applied but violated integrity rules during interview.",
         ["Docker","Linux"],
         "disqualified", rand_scores("zero"), 3, True),

        # ── Pending interview (applied, not yet done) ─────────────────────────
        (dev,    by_title["Backend Engineer"],
         "Interested in Python backend work.",
         ["Python","FastAPI","PostgreSQL"],
         "interview_pending", None, 0, False),

        (shreya, by_title["Product Manager"],
         "Product background, strong on discovery and roadmapping.",
         ["Product Strategy","User Research","Agile"],
         "interview_pending", None, 0, False),

        (arnav,  by_title["iOS Engineer"],
         "Has done some Swift on side projects.",
         ["Swift","SwiftUI"],
         "interview_pending", None, 0, False),

        (priya,  by_title["Computer Vision Engineer"],
         "Computer vision background from academic research.",
         ["Computer Vision","Python","OpenCV","PyTorch"],
         "interview_pending", None, 0, False),
    ]

    created_apps = []
    for (candidate, job, resume, skills, status, scores, viols, disq) in apps:
        app = upsert_application(
            candidate_id=candidate.id,
            job_id=job.id,
            resume_text=resume,
            resume_skills=skills,
            status=status,
            scores=scores,
            violations=viols,
            disqualified=disq,
        )
        # Add interview answers for completed interviews
        if status in ("shortlisted", "interviewed", "disqualified") and scores:
            qa = sample_answers(skills)
            if disq:
                qa[-1] = (qa[-1][0], "[Disqualified — interview terminated]")
            add_answers(app.id, qa)
        created_apps.append(app)

    db.commit()
    return created_apps


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n══════════════════════════════════════════════")
    print("  SmartHire — Database Seed")
    print("══════════════════════════════════════════════")

    hrs, candidates = seed_users()
    jobs = seed_jobs(hrs)
    apps = seed_applications(hrs, candidates, jobs)

    # Extract plain strings BEFORE closing the session.
    # Accessing ORM attributes after db.close() raises DetachedInstanceError
    # because SQLAlchemy can no longer lazy-load expired attributes.
    hr_emails        = [u.email for u in hrs]
    candidate_emails = [u.email for u in candidates]

    db.close()

    print("\n══════════════════════════════════════════════")
    print(f"  ✓ {len(hrs)} HR users")
    print(f"  ✓ {len(candidates)} candidates")
    print(f"  ✓ {len(jobs)} job openings")
    print(f"  ✓ {len(apps)} applications")
    print("══════════════════════════════════════════════")
    print("\nDemo credentials (all passwords: test123)")
    print("  HR logins:")
    for email in hr_emails:
        print(f"    {email}")
    print("  Candidate logins:")
    for email in candidate_emails:
        print(f"    {email}")
