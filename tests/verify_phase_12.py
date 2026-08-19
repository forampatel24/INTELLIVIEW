"""Verification of IntelliVue Phase 12 - Anti-Cheating Module.

Run: venv\\Scripts\\python.exe tests\\verify_phase_12.py
"""

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


# ---------------------------------------------------------------
print("=" * 64)
print("PHASE 12 - ANTI-CHEATING MODULE")
print("=" * 64)

from database.connection import execute

# --- Test user + session ---
from auth import login_user, register_user
EMAIL = "__phase12__@test.local"
try:
    auth_res = register_user("Phase12 User", EMAIL, "secret123", "user")
except ValueError:
    auth_res = login_user(EMAIL, "secret123")
user = auth_res["user"]

from ai.interview_engine import InterviewEngine
from ai.interview_engine.state import QuestionType as QT
engine = InterviewEngine(use_ai=False)
state = engine.start_session(user_id=user["id"], mode="resume", total_questions=1,
                             round_type=QT.THEORY)
check("test session ready", state.session_id is not None)

# --- Rules (pure, no DB) ---
from ai.anti_cheating.rules import (
    CONSECUTIVE_NO_FACE_TO_ESCALATE,
    CONSECUTIVE_LOOKING_AWAY_TO_ESCALATE,
    CONSECUTIVE_DROWSY_TO_ESCALATE,
    RuleContext,
    evaluate_event,
    evaluate_snapshot_rules,
)

from ai.face_monitor import CameraSnapshot


def snap(face=True, count=1, looking=False, drowsy=False, attention=100.0, head=0.0):
    return CameraSnapshot(
        face_detected=face, face_count=count, attention_score=attention,
        looking_away=looking, drowsy=drowsy, head_movement=head,
        eye_contact=not looking,
    )


ctx = RuleContext()
d0 = evaluate_snapshot_rules(snap(face=False), ctx)
check("no-face first frame -> low", len(d0) == 1 and d0[0].warning_type == "no_face" and d0[0].severity == "low", str(d0))

# Feed N-1 more no-face frames, then one more to cross the escalation threshold.
for _ in range(CONSECUTIVE_NO_FACE_TO_ESCALATE - 1):
    evaluate_snapshot_rules(snap(face=False), ctx)
d_escalate = evaluate_snapshot_rules(snap(face=False), ctx)
check("no-face sustained -> medium", any(d.severity == "medium" and d.warning_type == "no_face" for d in d_escalate), str(d_escalate))

ctx2 = RuleContext()
d_multi = evaluate_snapshot_rules(snap(count=2), ctx2)
check("multiple faces -> high", len(d_multi) == 1 and d_multi[0].severity == "high" and d_multi[0].warning_type == "multiple_faces", str(d_multi))

ctx3 = RuleContext()
d_away1 = evaluate_snapshot_rules(snap(looking=True), ctx3)
check("looking-away first -> medium", len(d_away1) == 1 and d_away1[0].severity == "medium" and d_away1[0].warning_type == "looking_away", str(d_away1))
for _ in range(CONSECUTIVE_LOOKING_AWAY_TO_ESCALATE - 1):
    evaluate_snapshot_rules(snap(looking=True), ctx3)
d_away2 = evaluate_snapshot_rules(snap(looking=True), ctx3)
check("looking-away sustained -> high", any(d.severity == "high" and d.warning_type == "looking_away" for d in d_away2), str(d_away2))

ctx4 = RuleContext()
d_drowsy1 = evaluate_snapshot_rules(snap(drowsy=True), ctx4)
check("drowsy first -> medium", len(d_drowsy1) == 1 and d_drowsy1[0].severity == "medium" and d_drowsy1[0].warning_type == "drowsiness", str(d_drowsy1))
for _ in range(CONSECUTIVE_DROWSY_TO_ESCALATE - 1):
    evaluate_snapshot_rules(snap(drowsy=True), ctx4)
d_drowsy2 = evaluate_snapshot_rules(snap(drowsy=True), ctx4)
check("drowsy sustained -> high", any(d.severity == "high" and d.warning_type == "drowsiness" for d in d_drowsy2), str(d_drowsy2))

ctx5 = RuleContext()
for _ in range(4):
    evaluate_snapshot_rules(snap(attention=20.0), ctx5)
d_att = evaluate_snapshot_rules(snap(attention=20.0), ctx5)
check("low attention sustained -> medium", any(d.warning_type == "low_attention" and d.severity == "medium" for d in d_att), str(d_att))

ctx6 = RuleContext()
for _ in range(4):
    evaluate_snapshot_rules(snap(head=0.9), ctx6)
d_head = evaluate_snapshot_rules(snap(head=0.9), ctx6)
check("head movement sustained -> medium", any(d.warning_type == "excessive_head_movement" and d.severity == "medium" for d in d_head), str(d_head))

# Recovered face resets counters -> next no-face fires low again.
ctx7 = RuleContext()
evaluate_snapshot_rules(snap(face=False), ctx7)
evaluate_snapshot_rules(snap(face=True), ctx7)
d_recover = evaluate_snapshot_rules(snap(face=False), ctx7)
check("recovery resets no-face counter", len(d_recover) == 1 and d_recover[0].severity == "low", str(d_recover))

ctx8 = RuleContext()
ctx8.consecutive_no_face = 3
ctx8.reset()
d_reset = evaluate_snapshot_rules(snap(face=False), ctx8)
check("context reset clears counters", len(d_reset) == 1 and d_reset[0].severity == "low")

d_tab = evaluate_event("tab_switch")
check("tab switch event -> high", d_tab is not None and d_tab.severity == "high" and d_tab.warning_type == "tab_switch", str(d_tab))
d_copy = evaluate_event("copy_paste", {"message": "text pasted"})
check("copy paste event -> medium", d_copy is not None and d_copy.severity == "medium", str(d_copy))
d_none = evaluate_event("not_suspicious")
check("benign event ignored", d_none is None, str(d_none))

# --- Service: risk scoring + verdicts ---
from ai.anti_cheating import AntiCheatingService, warning_summary_for_user

svc = AntiCheatingService()
check("empty risk is 0", svc.compute_risk_score([]) == 0.0, str(svc.compute_risk_score([])))

low_warnings = [{"severity": "low", "warning_type": "no_face"}]
check("risk positive with warnings", svc.compute_risk_score(low_warnings) > 0.0)

high_ones = [{"severity": "high", "warning_type": "multiple_faces"}] * 10
risk_flagged = svc.compute_risk_score(high_ones)
check("risk clamped <= 100", 0.0 <= risk_flagged <= 100.0, str(risk_flagged))
check("high warnings -> flagged zone", risk_flagged >= 60.0, str(risk_flagged))

mid_ones = [{"severity": "high", "warning_type": "multiple_faces"}] * 5
risk_susp = svc.compute_risk_score(mid_ones)
check("medium warnings -> suspicious zone", 30.0 <= risk_susp < 60.0, str(risk_susp))

clean_verdict = svc._build_verdict(1, 5.0, [{"severity": "low", "warning_type": "no_face"}])
check("low risk -> clean verdict", clean_verdict["status"] == "clean", str(clean_verdict))
susp_verdict = svc._build_verdict(1, risk_susp, mid_ones)
check("mid risk -> suspicious verdict", susp_verdict["status"] == "suspicious", str(susp_verdict))
flag_verdict = svc._build_verdict(1, risk_flagged, high_ones)
check("high risk -> flagged verdict", flag_verdict["status"] == "flagged", str(flag_verdict))
check("verdict shape", {"risk_score", "status", "warning_count", "warning_types", "severity_counts"} <= set(flag_verdict), str(flag_verdict))
check("severity counts break down", flag_verdict["severity_counts"]["high"] == 10, str(flag_verdict))

check("risk from metrics", 0.0 <= svc.risk_from_metrics(40.0, 0.2) <= 100.0)
check("risk from metrics higher when worse", svc.risk_from_metrics(40.0, 0.2) > svc.risk_from_metrics(90.0, 0.0))

# --- Engine: evaluation + persistence ---
from ai.anti_cheating import AntiCheatingEngine

callback_calls: list[tuple] = []


def on_warning(session_id, wtype, message, severity):
    callback_calls.append((session_id, wtype, message, severity))


cheat = AntiCheatingEngine(session_id=state.session_id, on_warning=on_warning)

# Two signals -> 2 decisions (no_face low on first, looking_away medium on first).
cheat.evaluate_snapshot(snap(face=False))
cheat.evaluate_snapshot(snap(looking=True))
warnings_now = cheat.service.get_warnings(state.session_id)
check("engine persists warnings", len(warnings_now) >= 2, str(warnings_now))
check("engine persists activity", len(cheat.service.get_activity_logs(state.session_id)) >= 2)
check("engine risk > 0", cheat.risk_score() > 0.0, str(cheat.risk_score()))

ev = cheat.evaluate_event("tab_switch")
check("engine event persisted", ev is not None and any(w["warning_type"] == "tab_switch" for w in cheat.service.get_warnings(state.session_id)))
check("engine callback fired", len(callback_calls) >= 3, str(callback_calls))

cheat2 = AntiCheatingEngine()
verdict_clean = cheat2.verdict_service.session_verdict(state.session_id)
check("session verdict computed", verdict_clean["risk_score"] >= 0.0 and verdict_clean["session_id"] == state.session_id, str(verdict_clean))

report = cheat2.verdict_service.session_report(state.session_id)
check("session report shape", {"session_id", "verdict", "camera_summary", "warning_summary"} <= set(report), str(report))
check("report warning summary counts", report["warning_summary"].get("looking_away", 0) >= 1, str(report["warning_summary"]))

rows = warning_summary_for_user(user["id"])
check("warning summary per user", any(r["session_id"] == state.session_id for r in rows), str(rows))

# --- CameraMonitor integration ---
import numpy as np
from ai.face_monitor import CameraMonitor

blank = np.zeros((240, 320, 3), dtype=np.uint8)
triggered_mon: list[tuple] = []


def mon_warning(session_id, wtype, message, severity):
    triggered_mon.append((session_id, wtype, message, severity))


cheat_mon = AntiCheatingEngine(session_id=state.session_id, on_warning=mon_warning)
monitor = CameraMonitor(service=cheat.service, log_interval_sec=0.0, anti_cheating=cheat_mon)
result = monitor.run(iter([blank, blank, blank]), session_id=state.session_id)
check("monitor processed frames with engine", result["frames_processed"] == 3, str(result))
no_face_rows = [w for w in cheat.service.get_warnings(state.session_id) if w["warning_type"] == "no_face"]
check("engine raised no_face through monitor", len(no_face_rows) >= 1, str(no_face_rows))
check("monitor callback through engine", any(w[1] == "no_face" for w in triggered_mon), str(triggered_mon))

# ---------------------------------------------------------------
print("=" * 64)
print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
print("=" * 64)
if failed:
    print("FAILED:", failed)

# cleanup
execute("DELETE FROM analytics")
execute("DELETE FROM activity_logs")
execute("DELETE FROM warnings")
execute("DELETE FROM eye_tracking")
execute("DELETE FROM camera_logs")
execute("DELETE FROM feedback")
execute("DELETE FROM reports")
execute("DELETE FROM interview_sessions")
execute("DELETE FROM users WHERE email=%s", (EMAIL,))
print("\ncleanup done")
sys.exit(1 if failed else 0)