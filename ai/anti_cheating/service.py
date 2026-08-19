"""Anti-cheating service: risk scoring and session verdicts.

Stateless reads over the warnings/camera logs persisted by CameraMonitoringService.
The risk model is a weighted sum of warning severities (recent warnings weighted
slightly more), clamped to 0-100.  Verdicts map the risk to a coarse status:
clean / suspicious / flagged.
"""

from typing import Optional

from ai.anti_cheating.rules import SEVERITY_WEIGHT, VERDICT_BOUNDARIES
from ai.face_monitor.service import CameraMonitoringService
from database.connection import query


class AntiCheatingService:
    def __init__(self, monitoring: Optional[CameraMonitoringService] = None):
        self.monitoring = monitoring or CameraMonitoringService()

    # --- Risk scoring ------------------------------------------------------

    @staticmethod
    def compute_risk_score(warnings: list[dict]) -> float:
        """0-100 weighted risk from warning rows (newest first)."""
        if not warnings:
            return 0.0
        total = 0.0
        for i, w in enumerate(warnings[:50]):
            weight = SEVERITY_WEIGHT.get(w.get("severity", "medium"), SEVERITY_WEIGHT["medium"])
            # Recent warnings count more; never below half weight.
            decay = max(0.5, 1.0 - i * 0.02)
            total += weight * decay
        return round(min(100.0, total), 2)

    # --- Verdicts ----------------------------------------------------------

    def session_verdict(self, session_id: int) -> dict:
        warnings = self.monitoring.get_warnings(session_id)
        risk = self.compute_risk_score(warnings)
        return self._build_verdict(session_id, risk, warnings)

    def _build_verdict(self, session_id: int, risk: float, warnings: list[dict]) -> dict:
        status = "clean"
        if risk >= VERDICT_BOUNDARIES["flagged"]:
            status = "flagged"
        elif risk >= VERDICT_BOUNDARIES["suspicious"]:
            status = "suspicious"
        return {
            "session_id": session_id,
            "risk_score": risk,
            "status": status,
            "warning_count": len(warnings),
            "warning_types": sorted({w["warning_type"] for w in warnings}),
            "severity_counts": {
                "low": sum(1 for w in warnings if w["severity"] == "low"),
                "medium": sum(1 for w in warnings if w["severity"] == "medium"),
                "high": sum(1 for w in warnings if w["severity"] == "high"),
            },
        }

    def session_report(self, session_id: int) -> dict:
        """A combined report: camera summary + warning summary + verdict."""
        verdict = self.session_verdict(session_id)
        camera = self.monitoring.session_summary(session_id)
        warning_summary = self.monitoring.session_warning_summary(session_id)
        return {
            "session_id": session_id,
            "verdict": verdict,
            "camera_summary": camera,
            "warning_summary": warning_summary,
        }

    # --- Risk flags used by the API layer ----------------------------------

    @staticmethod
    def risk_from_metrics(attention_avg: Optional[float], no_face_ratio: float) -> float:
        """Quick heuristic risk (0-100) from aggregate camera metrics."""
        risk = 0.0
        if attention_avg is not None:
            risk += max(0.0, (100.0 - attention_avg) * 0.4)
        risk += no_face_ratio * 100.0
        return round(min(100.0, risk), 2)


# Aggregate query used by higher layers to build dashboards / reports.
def warning_summary_for_user(user_id: int) -> list[dict]:
    """Per-session warning counts for one user, newest first."""
    return query(
        """
        SELECT s.id AS session_id, s.mode, s.created_at,
               COUNT(w.id) AS warning_count
        FROM interview_sessions s
        LEFT JOIN warnings w ON w.session_id = s.id
        WHERE s.user_id = %s
        GROUP BY s.id, s.mode, s.created_at
        ORDER BY s.created_at DESC
        """,
        (user_id,),
    )