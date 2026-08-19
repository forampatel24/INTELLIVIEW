"""Verification of IntelliVue Phase 11 - Camera Monitoring Service.

Run: venv\\Scripts\\python.exe tests\\verify_phase_11.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Use rule-based paths only (no AI keys needed for camera monitoring).
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
print("PHASE 11 - CAMERA MONITORING SERVICE")
print("=" * 64)

from database.connection import execute, query

# --- Test user + session ---
from auth import login_user, register_user
EMAIL = "__phase11__@test.local"
try:
    auth_res = register_user("Phase11 User", EMAIL, "secret123", "user")
except ValueError:
    auth_res = login_user(EMAIL, "secret123")
user = auth_res["user"]

from ai.interview_engine import InterviewEngine
from ai.interview_engine.state import QuestionType as QT
engine = InterviewEngine(use_ai=False)
state = engine.start_session(user_id=user["id"], mode="resume", total_questions=1,
                             round_type=QT.THEORY)
check("test session ready", state.session_id is not None)

# --- Geometry helpers with stub landmarks ---
from ai.face_monitor import geometry


class P:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def build_face(eye_gap: float, nose_x: float = 0.5, mouth_gap: float = 0.002):
    """Symmetrical stub face around x=0.5. eye_gap = vertical eye opening."""
    lm = [P(0.5, 0.5)] * 400
    lm[1] = P(nose_x, 0.5)          # nose tip
    # Eye corners: symmetric about 0.5, outer 0.40, inner 0.45 (left) etc.
    lm[33] = P(0.40, 0.45)          # left outer
    lm[133] = P(0.45, 0.45)         # left inner
    lm[362] = P(0.60, 0.45)         # right outer
    lm[263] = P(0.55, 0.45)         # right inner
    # Left eye EAR ring (33,159,158,133,153,144)
    lm[159] = P(0.415, 0.45 - eye_gap / 2)
    lm[158] = P(0.435, 0.45 - eye_gap / 2)
    lm[153] = P(0.435, 0.45 + eye_gap / 2)
    lm[144] = P(0.415, 0.45 + eye_gap / 2)
    # Right eye EAR ring (362,385,387,263,373,380)
    lm[385] = P(0.565, 0.45 - eye_gap / 2)
    lm[387] = P(0.585, 0.45 - eye_gap / 2)
    lm[373] = P(0.585, 0.45 + eye_gap / 2)
    lm[380] = P(0.565, 0.45 + eye_gap / 2)
    # Mouth
    lm[61] = P(0.45, 0.55)
    lm[291] = P(0.55, 0.55)
    lm[13] = P(0.5, 0.55 - mouth_gap / 2)
    lm[14] = P(0.5, 0.55 + mouth_gap / 2)
    return lm


lm_open = build_face(eye_gap=0.06)
ear_open = (geometry.eye_aspect_ratio(lm_open, geometry.EAR_LEFT) +
            geometry.eye_aspect_ratio(lm_open, geometry.EAR_RIGHT)) / 2
check("EAR high for open eyes", ear_open is not None and ear_open > 0.35, str(ear_open))

lm_closed = build_face(eye_gap=0.002)
ear_closed = (geometry.eye_aspect_ratio(lm_closed, geometry.EAR_LEFT) +
              geometry.eye_aspect_ratio(lm_closed, geometry.EAR_RIGHT)) / 2
check("EAR low for closed eyes", ear_closed is not None and ear_closed < 0.21, str(ear_closed))

# gaze: nose shifted far left -> looking away
lm_left_gaze = build_face(eye_gap=0.06, nose_x=0.42)
check("gaze offset detected", geometry.gaze_offset_x(lm_left_gaze) is not None)
check("looking away flagged", geometry.looking_away(lm_left_gaze) is True)
check("eye contact when centered", geometry.eye_contact(lm_open) is True)
mar = geometry.mouth_aspect_ratio(lm_open)
check("MAR computed", mar is not None and mar < 0.15, str(mar))

# --- Analyzer on synthetic frames ---
import numpy as np
from ai.face_monitor import FrameAnalyzer
analyzer = FrameAnalyzer()
blank = np.zeros((240, 320, 3), dtype=np.uint8)
snap_blank = analyzer.analyze(blank)
check("blank frame -> no face", snap_blank.face_detected is False and snap_blank.face_count == 0)
check("blank snapshot has attention", snap_blank.attention_score is None or snap_blank.attention_score >= 0)
check("snapshot to_db_row keys", set(snap_blank.to_db_row()) == {
    "face_detected", "face_count", "attention_score", "eye_contact", "looking_away",
    "head_movement", "drowsy", "smile_detected", "confidence"})

# --- Service persistence ---
from ai.face_monitor import CameraMonitoringService, CameraSnapshot
svc = CameraMonitoringService()
snap = CameraSnapshot(
    face_detected=True, face_count=1, attention_score=80.0, eye_contact=True,
    looking_away=False, head_movement=0.1, drowsy=False, smile_detected=True,
    confidence=0.9, gaze_x=0.02, gaze_y=0.01, blink_rate=12.0,
)
cam_id = svc.log_snapshot(state.session_id, snap)
check("camera_log row inserted", cam_id is not None and cam_id > 0)
eye_id = svc.log_eye(state.session_id, snap)
check("eye_tracking row inserted", eye_id is not None and eye_id > 0)
warn_id = svc.log_warning(state.session_id, "looking_away", "Looked away", "medium")
check("warning row inserted", warn_id is not None and warn_id > 0)
act_id = svc.log_activity(state.session_id, "camera_start", {"src": "test"})
check("activity row inserted", act_id is not None and act_id > 0)
an_id = svc.record_analytics(user["id"], "camera_samples", 1.0)
check("analytics row inserted", an_id is not None and an_id > 0)

logs = svc.get_camera_logs(state.session_id)
check("camera logs readable", len(logs) >= 1 and logs[0]["face_detected"] == 1)
eyes = svc.get_eye_tracking(state.session_id)
check("eye tracking readable", len(eyes) >= 1 and eyes[0]["blink_rate"] == 12.0)
warns = svc.get_warnings(state.session_id)
check("warnings readable", len(warns) >= 1 and warns[0]["warning_type"] == "looking_away")
acts = svc.get_activity_logs(state.session_id)
check("activity readable", len(acts) >= 1 and acts[0]["event_type"] == "camera_start")
an_rows = svc.get_analytics(user_id=user["id"], metric_name="camera_samples")
check("analytics readable", len(an_rows) >= 1 and an_rows[0]["metric_value"] == 1.0)

summary = svc.session_summary(state.session_id)
check("session summary", summary["camera_samples"] >= 1 and summary["warning_count"] >= 1, str(summary))
wsummary = svc.session_warning_summary(state.session_id)
check("warning summary grouped", wsummary.get("looking_away", 0) >= 1, str(wsummary))

# --- CameraMonitor over synthetic frames ---
from ai.face_monitor import CameraMonitor

triggered: list[tuple] = []


def fake_warning(session_id, wtype, message, severity):
    triggered.append((session_id, wtype, message, severity))


frames = [blank] * 3
monitor = CameraMonitor(analyzer=analyzer, service=svc, log_interval_sec=0.0,
                        on_warning=fake_warning)
result = monitor.run(iter(frames), session_id=state.session_id)
check("monitor processed frames", result["frames_processed"] == 3, str(result))
check("monitor logged snapshots", result["snapshots_logged"] >= 1, str(result))
check("monitor no-face warning fired", any(w[1] == "no_face" for w in triggered), str(triggered))

# Monitor with fake face detection on a blank frame would need a real face;
# instead verify the stop flag path and per-frame processing.
monitor2 = CameraMonitor(analyzer=analyzer, service=svc, log_interval_sec=0.0)
monitor2.process_frame(blank)
monitor2.process_frame(blank)
check("per-frame processing", monitor2.frames_processed == 2)

# --- EyeTracker package ---
from ai.eye_tracker import EyeTracker
tracker = EyeTracker()
tr = tracker.track(blank)
check("eye tracker no face", tr["face_detected"] is False and tr["gaze_x"] is None)
check("eye tracker keys", {"gaze_x", "gaze_y", "eye_contact", "looking_away", "drowsy"} <= set(tr))

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