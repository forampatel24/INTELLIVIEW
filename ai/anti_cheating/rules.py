"""Anti-cheating rules: pure evaluation of snapshots and events.

Rules are deliberately separated from persistence so they can be unit-tested
without a database.  Each rule inspects a CameraSnapshot (or an external event)
plus the current temporal context (consecutive-frame counters) and returns
zero or more WarningDecision objects.

Severity progression follows a "first occurrence, then escalate" pattern:
the first frame of a signal raises a low/medium warning, and sustained
signals (consecutive frames) escalate to a higher severity.
"""

from dataclasses import dataclass
from typing import Optional

from ai.face_monitor.analyzer import CameraSnapshot

# --- Rule configuration ----------------------------------------------------

CONSECUTIVE_NO_FACE_TO_ESCALATE = 10
CONSECUTIVE_LOOKING_AWAY_TO_ESCALATE = 8
CONSECUTIVE_DROWSY_TO_ESCALATE = 6
CONSECUTIVE_MULTI_FACE_TO_ESCALATE = 3
CONSECUTIVE_LOW_ATTENTION_TO_ESCALATE = 5
CONSECUTIVE_HEAD_MOVEMENT_TO_ESCALATE = 5

LOW_ATTENTION_THRESHOLD = 50.0
HIGH_HEAD_MOVEMENT_THRESHOLD = 0.5

SEVERITY_WEIGHT = {"low": 1, "medium": 3, "high": 7}

# Risk-score boundaries for verdicts (see service.compute_risk_score).
VERDICT_BOUNDARIES = {"suspicious": 30.0, "flagged": 60.0}

# --- Decisions -------------------------------------------------------------


@dataclass
class WarningDecision:
    warning_type: str
    message: str
    severity: str = "medium"


# --- Temporal context ------------------------------------------------------


class RuleContext:
    """Consecutive-frame counters consulted by the rules.

    The engine owns one context per session; rules mutate it as they are
    evaluated so that sustained behavior escalates appropriately.
    """

    def __init__(self):
        self.consecutive_no_face = 0
        self.consecutive_looking_away = 0
        self.consecutive_drowsy = 0
        self.consecutive_multiple_faces = 0
        self.consecutive_low_attention = 0
        self.consecutive_head_movement = 0

    def reset(self):
        for attr in list(self.__dict__):
            setattr(self, attr, 0)


# --- Snapshot rules --------------------------------------------------------


def evaluate_snapshot_rules(snapshot: CameraSnapshot, ctx: RuleContext) -> list[WarningDecision]:
    """Evaluates one camera snapshot against all rules.

    ``ctx`` is mutated in place so callers can reuse a session's context.
    """
    decisions: list[WarningDecision] = []

    if not snapshot.face_detected:
        ctx.consecutive_no_face += 1
        ctx.consecutive_looking_away = 0
        ctx.consecutive_drowsy = 0
        ctx.consecutive_multiple_faces = 0
        ctx.consecutive_low_attention = 0
        ctx.consecutive_head_movement = 0
        if ctx.consecutive_no_face == 1:
            decisions.append(WarningDecision("no_face", "No face detected", "low"))
        elif ctx.consecutive_no_face >= CONSECUTIVE_NO_FACE_TO_ESCALATE:
            decisions.append(WarningDecision("no_face", "Face not detected for an extended period", "medium"))
        return decisions

    ctx.consecutive_no_face = 0

    # Multiple faces is always high.
    if snapshot.face_count > 1:
        ctx.consecutive_multiple_faces += 1
        if ctx.consecutive_multiple_faces == 1:
            decisions.append(WarningDecision("multiple_faces", f"Detected {snapshot.face_count} faces", "high"))
    else:
        ctx.consecutive_multiple_faces = 0

    # Looking away.
    if snapshot.looking_away:
        ctx.consecutive_looking_away += 1
        if ctx.consecutive_looking_away == 1:
            decisions.append(WarningDecision("looking_away", "Candidate looked away from camera", "medium"))
        elif ctx.consecutive_looking_away >= CONSECUTIVE_LOOKING_AWAY_TO_ESCALATE:
            decisions.append(WarningDecision("looking_away", "Looking away from camera for an extended period", "high"))
    else:
        ctx.consecutive_looking_away = 0

    # Drowsiness / closed eyes.
    if snapshot.drowsy:
        ctx.consecutive_drowsy += 1
        if ctx.consecutive_drowsy == 1:
            decisions.append(WarningDecision("drowsiness", "Candidate appears drowsy or eyes closed", "medium"))
        elif ctx.consecutive_drowsy >= CONSECUTIVE_DROWSY_TO_ESCALATE:
            decisions.append(WarningDecision("drowsiness", "Drowsiness sustained for an extended period", "high"))
    else:
        ctx.consecutive_drowsy = 0

    # Low attention score.
    if snapshot.attention_score is not None and snapshot.attention_score < LOW_ATTENTION_THRESHOLD:
        ctx.consecutive_low_attention += 1
        if ctx.consecutive_low_attention >= CONSECUTIVE_LOW_ATTENTION_TO_ESCALATE:
            decisions.append(WarningDecision("low_attention", "Low attention score sustained", "medium"))
    else:
        ctx.consecutive_low_attention = 0

    # Excessive head movement.
    if snapshot.head_movement is not None and snapshot.head_movement > HIGH_HEAD_MOVEMENT_THRESHOLD:
        ctx.consecutive_head_movement += 1
        if ctx.consecutive_head_movement >= CONSECUTIVE_HEAD_MOVEMENT_TO_ESCALATE:
            decisions.append(WarningDecision("excessive_head_movement", "Excessive head movement sustained", "medium"))
    else:
        ctx.consecutive_head_movement = 0

    return decisions


# --- Event rules -----------------------------------------------------------

# External (non-camera) events reported by the client or proctor layer.
EVENT_SEVERITY = {
    "tab_switch": "high",
    "copy_paste": "medium",
    "fullscreen_exit": "medium",
    "suspect_shortcut": "high",
}


def evaluate_event(event_type: str, event_data: Optional[dict] = None) -> Optional[WarningDecision]:
    """Evaluates a non-camera event; returns None if the event is not suspect."""
    severity = EVENT_SEVERITY.get(event_type)
    if severity is None:
        return None
    message = event_type
    if event_data and isinstance(event_data.get("message"), str):
        message = event_data["message"]
    return WarningDecision(event_type, message, severity)