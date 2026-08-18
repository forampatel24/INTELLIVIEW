"""Verification of IntelliVue Phase 10 - Report Generator.

Run: venv\\Scripts\\python.exe tests\\verify_phase_10.py
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
os.environ["REPORT_PROVIDER"] = "mock"

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
print("PHASE 10 - REPORT GENERATOR")
print("=" * 64)

from ai.report_generator import (
    ReportGenerator,
    build_radar_data,
    build_heatmap_data,
    build_timeline_data,
    build_strengths,
    build_weaknesses,
    build_suggestions,
    build_learning_resources,
    build_recruiter_summary,
)
from ai.interview_engine import InterviewEngine
from ai.interview_engine.state import QuestionType as QT
from ai.feedback_engine.metrics import FeedbackMetrics
from database.connection import execute, query

# --- Create a real user (interview_sessions FK -> users) ---
from auth import login_user, register_user
EMAIL = "__phase10__@test.local"
try:
    auth_res = register_user("Phase10 User", EMAIL, "secret123", "user")
except ValueError:
    auth_res = login_user(EMAIL, "secret123")
user = auth_res["user"]
check("test user ready", user["email"] == EMAIL)

# --- Build a completed session (mirrors phase 6 flow) ---
engine = InterviewEngine(use_ai=False)
state = engine.start_session(
    user_id=user["id"], mode="resume", total_questions=4,
    round_type=QT.THEORY,
    resume_data={"skills": ["Python", "SQL", "React"], "sections": {}},
)
check("session started", state.session_id is not None)
for i in range(4):
    engine.get_current_question(state)
    engine.submit_answer(state, answer_text="solid answer")
final = engine.next_question(state)
check("session completes", final["is_complete"])

# --- Data builders ---
metrics = FeedbackMetrics.compute(state)
radar = build_radar_data(state, metrics)
check("radar data has >=3 axes", len(radar) >= 3, str(radar))
check("radar axes have scores", all(0 <= ax["score"] <= 100 for ax in radar))
heat = build_heatmap_data(state, metrics)
check("heatmap shape (3 difficulties)", len(heat["values"]) == 3, str(len(heat["values"])))
check("heatmap shape (5 types)", all(len(row) == 5 for row in heat["values"]))
timeline = build_timeline_data(state, metrics)
check("timeline length == answers", len(timeline) == len(state.answers), str(len(timeline)))
strengths = build_strengths(metrics)
weaknesses = build_weaknesses(metrics)
check("strengths non-empty", len(strengths) >= 1)
check("weaknesses non-empty", len(weaknesses) >= 1)
suggestions = build_suggestions(metrics, weaknesses)
check("suggestions non-empty", len(suggestions) >= 1)
resources = build_learning_resources(weaknesses, metrics)
check("learning resources non-empty", len(resources) >= 1)
check("resources have topic+resource", all("topic" in r and "resource" in r for r in resources))
summary = build_recruiter_summary(metrics, "hire", strengths)
check("recruiter summary text", len(summary) > 30, summary)

# --- ReportGenerator end-to-end ---
rg = ReportGenerator(use_ai=True)  # mock provider
report = rg.generate_report(state)
check("report generated", report["report_id"] is not None)
check("recommendation valid", report["recommendation"] in ("hire", "maybe", "reject"))
check("recruiter_summary present", len(report["recruiter_summary"]) > 30)
check("full_report has radar", isinstance(report["radar_data"], list) and len(report["radar_data"]) >= 3)
check("full_report has heatmap", report["heatmap_data"]["values"])
check("full_report has timeline", report["timeline_data"])
check("report persisted", bool(query("SELECT id FROM reports WHERE session_id=%s", (state.session_id,))))
check("report readable via get_report", rg.get_report(state.session_id) is not None)
stored = rg.get_report(state.session_id)
check("stored JSON decoded", isinstance(stored.get("radar_data"), list))

# --- list_for_user ---
# Create a user + session ownership link to test the join
# --- list_for_user ---
reports_list = rg.list_for_user(user["id"])
check("list_for_user returns report", any(r["session_id"] == state.session_id for r in reports_list))

# --- Reject recommendation path (low scores) ---
engine3 = InterviewEngine(use_ai=False)
state3 = engine3.start_session(user_id=user["id"], mode="resume", total_questions=2, round_type=QT.THEORY)
for i in range(2):
    engine3.get_current_question(state3)
    engine3.submit_answer(state3, answer_text="")
final3 = engine3.next_question(state3)
report3 = rg.generate_report(state3)
check("low-score recommendation", report3["recommendation"] in ("maybe", "reject"), report3["recommendation"])

# ---------------------------------------------------------------
print("=" * 64)
print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
print("=" * 64)
if failed:
    print("FAILED:", failed)

# cleanup
execute("DELETE FROM reports")
execute("DELETE FROM feedback")
execute("DELETE FROM interview_sessions")
execute("DELETE FROM users WHERE email=%s", ("__phase10__@test.local",))
print("\ncleanup done")
sys.exit(1 if failed else 0)