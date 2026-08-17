"""Comprehensive verification of IntelliVue phases 1-9.

Run: venv\\Scripts\\python.exe tests\\verify_phases_1_9.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["RESUME_PROVIDER"] = "mock"
os.environ["QUESTION_PROVIDER"] = "mock"
os.environ["EVALUATION_PROVIDER"] = "mock"
os.environ["BEHAVIOR_PROVIDER"] = "mock"
os.environ["FEEDBACK_PROVIDER"] = "mock"

from services.llm.router import get_router
get_router.cache_clear()

passed: list[str] = []
failed: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        passed.append(name)
        print(f"  [PASS] {name}")
    else:
        failed.append(name)
        print(f"  [FAIL] {name} {detail}")


PROJECT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 1 - PROJECT SCAFFOLDING")
print("=" * 64)
required_dirs = [
    "ai/resume_parser", "ai/interview_engine", "ai/feedback_engine",
    "ai/domains", "ai/question_bank", "ai/face_monitor", "ai/eye_tracker",
    "ai/emotion_detector", "ai/report_generator", "backend/routers",
    "database/migrations", "storage/uploads", "storage/recordings",
    "models", "prompts", "services/llm", "utils", "logs", "analytics", "tests", "docs",
]
missing_dirs = [d for d in required_dirs if not (PROJECT / d).is_dir()]
check("all phase-1 dirs exist", not missing_dirs, f"missing={missing_dirs}")
check("requirements.txt exists", (PROJECT / "requirements.txt").is_file())
check(".env exists", (PROJECT / ".env").is_file())
check("venv exists", (PROJECT / "venv").is_dir())
check("legacy preserved", (PROJECT / "legacy").is_dir())

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 2 - AI MULTI-PROVIDER LAYER")
print("=" * 64)
from services.llm import TASKS, LLMError, router
check("TASKS defined", len(TASKS) == 5, str(TASKS))
check("all 5 tasks route", all(router.provider_for(t) for t in TASKS))
mock_resp = router.generate("question_generation", "hi")
check("mock provider responds", mock_resp.text.startswith("[mock:"))
try:
    from services.llm.providers import GeminiProvider
    GeminiProvider(api_key="")
    check("empty gemini key raises", False)
except LLMError:
    check("empty gemini key raises", True)

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 3 - DATABASE SETUP")
print("=" * 64)
from database.connection import execute, query
tables = {r["Tables_in_intellivue"] for r in query("SHOW TABLES")}
expected_tables = {
    "users", "resumes", "domains", "skills", "interview_sessions", "questions",
    "answers", "feedback", "reports", "achievements", "warnings", "camera_logs",
    "eye_tracking", "activity_logs", "analytics", "schema_migrations",
}
check("all tables exist", tables >= expected_tables, f"missing={expected_tables - tables}")
mig = {r["filename"] for r in query("SELECT filename FROM schema_migrations")}
check("migrations 0001+0002 applied", {"0001_initial_schema.sql", "0002_domains_focus_skills.sql"} <= mig, str(mig))
# roundtrip insert/select/delete
tmp_id = execute("INSERT INTO domains (name, category) VALUES (%s,%s)", ("_verify_tmp", "test"))
row = query("SELECT name FROM domains WHERE id=%s", (tmp_id,))
check("db insert/select works", row and row[0]["name"] == "_verify_tmp")
execute("DELETE FROM domains WHERE id=%s", (tmp_id,))
check("db delete works", not query("SELECT id FROM domains WHERE id=%s", (tmp_id,)))

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 4 - AUTH MODULE")
print("=" * 64)
from auth import decode_token, login_user, register_user
EMAIL = "verify.phases@vit.edu"
try:
    auth_res = register_user("Verify Phases", EMAIL, "secret123", "user")
except ValueError:
    auth_res = login_user(EMAIL, "secret123")
user = auth_res["user"]
check("register/login works", user["email"] == EMAIL)
check("access token issued", bool(auth_res.get("access_token")))
check("refresh token issued", bool(auth_res.get("refresh_token")))
check("token decodes", decode_token(auth_res["access_token"])["sub"] == str(user["id"]))
try:
    register_user("Dup", EMAIL, "secret123")
    check("duplicate email rejected", False)
except ValueError:
    check("duplicate email rejected", True)
try:
    register_user("Bad", "not-an-email", "secret123")
    check("invalid email rejected", False)
except ValueError:
    check("invalid email rejected", True)

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 5 - RESUME PARSER")
print("=" * 64)
from ai.resume_parser import ResumeParser
resume_pdf = PROJECT / "storage" / "uploads" / "sample_resume.pdf"
check("sample resume exists", resume_pdf.is_file())
if resume_pdf.is_file():
    parser = ResumeParser(use_ai=False)
    parsed = parser.parse_pdf(str(resume_pdf))
    check("resume text extracted", len(parsed.get("parsed_text", "")) > 500)
    check("contact extracted", "@" in parsed.get("contact", {}).get("email", ""))
    check("skills extracted (>=15)", len(parsed.get("skills", [])) >= 15,
          str(len(parsed.get("skills", []))))
    check("sections detected", {"education", "skills", "projects", "certifications"} <= set(parsed.get("sections", {})),
          str(list(parsed.get("sections", {}).keys())))
    from ai.resume_parser.ats_scorer import ATSScorer
    ats = ATSScorer().score(parsed["sections"], parsed["parsed_text"], parsed["skills"])
    check("ATS score computed", 0 <= ats["score"] <= 100, str(ats["score"]))

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 6 - INTERVIEW ENGINE")
print("=" * 64)
from ai.interview_engine import InterviewEngine, QuestionType
from ai.interview_engine.experience import detect_years_of_experience
from ai.interview_engine.difficulty import DifficultySelector
engine = InterviewEngine(use_ai=False)
state = engine.start_session(
    user_id=user["id"], mode="resume", total_questions=3,
    round_type=QuestionType.THEORY,
    resume_data={"skills": ["Python", "C++", "Java"], "sections": {}},
)
check("session started", state.session_id is not None)
check("focus skills flow through", state.focus_skills[:3] == ["Python", "C++", "Java"], str(state.focus_skills[:3]))
check("years detection", detect_years_of_experience({"years_of_experience": "3+ years"}) == 3.0)
sel = DifficultySelector()
check("adaptive diff one-step up", sel.next_difficulty(__import__("ai.interview_engine.state", fromlist=["Difficulty"]).Difficulty.EASY, [90, 95]).value == "medium")
check("adaptive diff one-step down", sel.next_difficulty(__import__("ai.interview_engine.state", fromlist=["Difficulty"]).Difficulty.HARD, [20, 10]).value == "medium")
# multi-step progression: easy -> medium -> hard with sustained strong scores
d = __import__("ai.interview_engine.state", fromlist=["Difficulty"]).Difficulty.EASY
for s in [95, 90, 92]:
    d = sel.next_difficulty(d, [s])
check("adaptive diff escalates to hard", d.value == "hard", d.value)
for i in range(3):
    q = engine.get_current_question(state)
    check(f"Q{i+1} generated", bool(q["text"]))
    engine.submit_answer(state, answer_text="solid answer")
final = engine.next_question(state)
check("session completes", final["is_complete"])
check("overall score", 0 <= final["overall_score"] <= 100)
check("session persisted", bool(query("SELECT id FROM interview_sessions WHERE id=%s", (state.session_id,))))

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 7 - DOMAIN SYSTEM")
print("=" * 64)
from ai.domains import DomainService
dsvc = DomainService()
seed = dsvc.seed()
check("seed idempotent", seed["inserted"] == 0, str(seed))
domains = dsvc.list_domains()
check("31 domains", len(domains) == 31, str(len(domains)))
check("7 categories", len(dsvc.list_categories()) == 7, str(dsvc.list_categories()))
names = {d["name"] for d in domains}
required_domains = {"Python", "C++", "Java", "React", "SQL", "DBMS", "Operating Systems",
                    "Computer Networks", "System Design", "DevOps", "Cloud", "Linux",
                    "Machine Learning", "Deep Learning", "Artificial Intelligence",
                    "Data Science", "Business Intelligence", "Tableau", "Cybersecurity",
                    "HR", "Behavioral", "Managerial", "Finance", "Marketing", "Sales",
                    "Business Analytics", "Case Study", "Aptitude"}
check("all required domains", required_domains <= names, f"missing={required_domains - names}")
py_domain = dsvc.get_domain(name="Python")
check("domain has focus skills", len(py_domain["focus_skills"]) >= 4)

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 8 - QUESTION BANK & ROUNDS")
print("=" * 64)
from ai.question_bank import QuestionBankService
from ai.interview_engine.state import Difficulty, QuestionType as QT
bank = QuestionBankService()
bank_seed = bank.seed()
check("bank seed idempotent", bank_seed["inserted"] == 0, str(bank_seed))
check("bank has questions", bank.count() >= 50, str(bank.count()))
mcqs = bank.list_questions(question_type=QT.MCQ)
check("MCQs have answer keys", all(q.correct_answer for q in mcqs), "some MCQs lack keys")
check("all 5 round types", {q.question_type for q in bank.list_questions()} == set(QT),
      str({q.question_type for q in bank.list_questions()}))
check("all 3 difficulties", {q.difficulty for q in bank.list_questions()} == set(Difficulty))
# bank integration into engine (domain mode)
engine2 = InterviewEngine(use_ai=False, bank=bank)
state2 = engine2.start_session(user_id=user["id"], mode="domain", total_questions=1,
                               domain_id=py_domain["id"], round_type=QT.MCQ,
                               focus_skills=py_domain["focus_skills"])
q = engine2.get_current_question(state2)
check("domain mode uses bank", bool(q.get("options")) and q["type"] == "mcq", str(q.get("text")))
res = engine2.submit_answer(state2, selected_option="C")
check("mcq auto-graded", res["score"] in (0.0, 100.0), str(res["score"]))

# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 9 - FEEDBACK ENGINE")
print("=" * 64)
from ai.feedback_engine import FeedbackEngine, FeedbackMetrics
fb = FeedbackEngine(use_ai=True)  # mock provider
fb_result = fb.generate_feedback(state)
check("feedback generated", fb_result["feedback_id"] is not None)
check("recommendation valid", fb_result["recommendation"] in ("hire", "maybe", "reject"))
check("metrics computed", "overall_score" in fb_result["metrics"])
check("skills breakdown", isinstance(fb_result["metrics"]["skills"], dict))
check("feedback persisted", bool(query("SELECT id FROM feedback WHERE session_id=%s", (state.session_id,))))
check("feedback readable", fb.get_feedback(state.session_id) is not None)

# ---------------------------------------------------------------
print("=" * 64)
print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
print("=" * 64)
if failed:
    print("FAILED:", failed)

# cleanup
execute("DELETE FROM feedback")
execute("DELETE FROM interview_sessions")
execute("DELETE FROM users WHERE email=%s", (EMAIL,))
print("\ncleanup done")
sys.exit(1 if failed else 0)