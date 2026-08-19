"""AntiCheatingEngine: evaluates monitoring signals against anti-cheating rules.

Owns one temporal RuleContext per session, evaluates camera snapshots and
external events against the rules, and persists raised warnings to the
``warnings`` / ``activity_logs`` tables via CameraMonitoringService.

The engine is also the ``on_warning`` / ``on_cheat_event`` sink that a
CameraMonitor (phase 11) or an API endpoint calls with raw events.
"""

from typing import Callable, Optional

from ai.anti_cheating.rules import (
    RuleContext,
    WarningDecision,
    evaluate_event,
    evaluate_snapshot_rules,
)
from ai.anti_cheating.service import AntiCheatingService
from ai.face_monitor.analyzer import CameraSnapshot
from ai.face_monitor.service import CameraMonitoringService

WarningSink = Callable[[int, str, str, str], None]

# activity_logs.severity is ENUM('info','warning','critical'); map the
# warnings-table severities onto it.
ACTIVITY_SEVERITY = {"low": "warning", "medium": "warning", "high": "critical"}


class AntiCheatingEngine:
    def __init__(
        self,
        session_id: Optional[int] = None,
        service: Optional[CameraMonitoringService] = None,
        on_warning: Optional[WarningSink] = None,
    ):
        self.session_id = session_id
        self.service = service or CameraMonitoringService()
        self.verdict_service = AntiCheatingService(monitoring=self.service)
        self.on_warning = on_warning
        self._context = RuleContext()
        self._raised: list[WarningDecision] = []

    # --- Camera snapshots ---------------------------------------------------

    def evaluate_snapshot(self, snapshot: CameraSnapshot, session_id: Optional[int] = None) -> list[WarningDecision]:
        """Runs snapshot rules, persists any warnings, returns decisions."""
        if session_id is not None:
            self.session_id = session_id
        decisions = evaluate_snapshot_rules(snapshot, self._context)
        for d in decisions:
            self._raise(d)
        return decisions

    # --- External events ----------------------------------------------------

    def evaluate_event(self, event_type: str, event_data: Optional[dict] = None, session_id: Optional[int] = None) -> Optional[WarningDecision]:
        """Evaluates a non-camera event (tab switch, copy/paste, etc.)."""
        if session_id is not None:
            self.session_id = session_id
        decision = evaluate_event(event_type, event_data)
        if decision is not None:
            self._raise(decision)
        return decision

    # --- Session status ------------------------------------------------------

    def risk_score(self, session_id: Optional[int] = None) -> float:
        return self.verdict_service.compute_risk_score(self._warnings(session_id))

    def verdict(self, session_id: Optional[int] = None) -> dict:
        sid = session_id or self.session_id
        warnings = self._warnings(sid)
        risk = self.verdict_service.compute_risk_score(warnings)
        return self.verdict_service._build_verdict(sid, risk, warnings)

    def reset(self):
        self._context.reset()
        self._raised.clear()

    # --- Internals ----------------------------------------------------------

    def _warnings(self, session_id: Optional[int]) -> list[dict]:
        sid = session_id or self.session_id
        if sid is None:
            return []
        return self.service.get_warnings(sid)

    def _raise(self, decision: WarningDecision):
        self._raised.append(decision)
        if self.session_id is None:
            return
        self.service.log_warning(self.session_id, decision.warning_type, decision.message, decision.severity)
        self.service.log_activity(
            self.session_id,
            "anti_cheating",
            {"warning_type": decision.warning_type, "severity": decision.severity, "message": decision.message},
            severity=ACTIVITY_SEVERITY.get(decision.severity, "warning"),
        )
        if self.on_warning is not None:
            self.on_warning(self.session_id, decision.warning_type, decision.message, decision.severity)