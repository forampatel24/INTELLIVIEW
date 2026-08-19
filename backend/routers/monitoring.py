"""Anti-cheating monitoring endpoints (phase 15)."""

from fastapi import APIRouter, Depends, HTTPException

from ai.anti_cheating import AntiCheatingService
from auth.dependencies import get_current_user
from database.connection import fetch_one

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/{session_id}")
def monitoring_verdict(session_id: int, user: dict = Depends(get_current_user)):
    _check_ownership(session_id, user)
    return AntiCheatingService().session_verdict(session_id)


@router.get("/{session_id}/report")
def monitoring_report(session_id: int, user: dict = Depends(get_current_user)):
    _check_ownership(session_id, user)
    return AntiCheatingService().session_report(session_id)


def _check_ownership(session_id: int, user: dict) -> None:
    session = fetch_one(
        "SELECT user_id FROM interview_sessions WHERE id = %s", (session_id,)
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user["id"] and user["role"] not in ("admin", "recruiter"):
        raise HTTPException(status_code=403, detail="Not your session")