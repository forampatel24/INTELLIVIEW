"""Anti-cheating module (phase 12).

Rules evaluate camera snapshots and external events into graded warnings, the
engine owns per-session temporal context and persistence, and the service
computes risk scores and session verdicts (clean / suspicious / flagged).
"""

from ai.anti_cheating.engine import AntiCheatingEngine
from ai.anti_cheating.rules import RuleContext, WarningDecision
from ai.anti_cheating.service import AntiCheatingService, warning_summary_for_user

__all__ = [
    "AntiCheatingEngine",
    "AntiCheatingService",
    "RuleContext",
    "WarningDecision",
    "warning_summary_for_user",
]