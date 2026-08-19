"""Interview flow endpoints (phase 15).

Exposes the InterviewEngine pipeline over HTTP: start a session, fetch the
current question, submit answers, generate feedback, and retrieve reports.
State is reloaded from MySQL on every request via InterviewSessionService.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ai.anti_cheating import AntiCheatingEngine
from ai.feedback_engine import FeedbackEngine
from ai.interview_engine import InterviewEngine
from ai.interview_engine.session_service import InterviewSessionService
from ai.interview_engine.state import InterviewState, QuestionType
from ai.report_generator import ReportGenerator
from auth.dependencies import get_current_user
from database.connection import fetch_one, query

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


class StartRequest(BaseModel):
    mode: str = "resume"
    total_questions: int = 5
    resume_id: Optional[int] = None
    domain_id: Optional[int] = None
    round_type: str = "theory"


class AnswerRequest(BaseModel):
    answer_text: Optional[str] = None
    selected_option: Optional[str] = None
    code_submitted: Optional[str] = None
    time_taken_sec: int = 0


class CheatEventRequest(BaseModel):
    event_type: str
    event_data: Optional[dict] = None


@router.post("/start", status_code=201)
def start_interview(body: StartRequest, user: dict = Depends(get_current_user)):
    if body.total_questions < 1 or body.total_questions > 30:
        raise HTTPException(status_code=400, detail="total_questions must be 1-30")
    try:
        round_type = QuestionType(body.round_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid round_type") from exc

    resume_data = None
    if body.resume_id:
        resume = fetch_one(
            "SELECT parsed_json FROM resumes WHERE id = %s AND user_id = %s",
            (body.resume_id, user["id"]),
        )
        if resume and resume.get("parsed_json"):
            try:
                resume_data = json.loads(resume["parsed_json"])
            except json.JSONDecodeError:
                resume_data = None

    engine = InterviewEngine(use_ai=True)
    state = engine.start_session(
        user_id=user["id"],
        mode=body.mode,
        total_questions=body.total_questions,
        resume_data=resume_data,
        resume_id=body.resume_id,
        domain_id=body.domain_id,
        round_type=round_type,
    )
    question = engine.get_current_question(state)
    return {"session_id": state.session_id, "state": state.state_dict, "question": question}


@router.get("")
def list_sessions(user: dict = Depends(get_current_user)):
    return query(
        """
        SELECT id, mode, difficulty, status, total_questions, current_question_index,
               overall_score, integrity_score, created_at, started_at, ended_at
        FROM interview_sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 50
        """,
        (user["id"],),
    )


@router.get("/{session_id}/state")
def session_state(session_id: int, user: dict = Depends(get_current_user)):
    state = _load_owned_state(session_id, user)
    return state.state_dict


@router.get("/{session_id}/question")
def current_question(session_id: int, user: dict = Depends(get_current_user)):
    state = _load_owned_state(session_id, user)
    engine = InterviewEngine(use_ai=True)
    question = engine.get_current_question(state)
    return {"state": state.state_dict, "question": question}


@router.post("/{session_id}/answer")
def submit_answer(session_id: int, body: AnswerRequest, user: dict = Depends(get_current_user)):
    state = _load_owned_state(session_id, user)
    if state.is_complete:
        raise HTTPException(status_code=400, detail="Interview already complete")
    engine = InterviewEngine(use_ai=True)
    result = engine.submit_answer(
        state,
        answer_text=body.answer_text,
        selected_option=body.selected_option,
        code_submitted=body.code_submitted,
        time_taken_sec=body.time_taken_sec,
    )
    overall = None
    if result["is_complete"]:
        final = engine.next_question(state)  # marks session completed
        overall = final["overall_score"]
    return {
        "score": result["score"],
        "feedback": result["feedback"],
        "next_difficulty": result["next_difficulty"],
        "is_complete": result["is_complete"],
        "overall_score": overall,
        "state": state.state_dict,
    }


@router.post("/{session_id}/feedback")
def generate_feedback(session_id: int, user: dict = Depends(get_current_user)):
    state = _load_owned_state(session_id, user)
    if not state.answers:
        raise HTTPException(status_code=400, detail="No answers yet; cannot generate feedback")
    try:
        return FeedbackEngine(use_ai=True).generate_feedback(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}/feedback")
def get_feedback(session_id: int, user: dict = Depends(get_current_user)):
    _load_owned_state(session_id, user)
    feedback = FeedbackEngine(use_ai=True).get_feedback(session_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if isinstance(feedback.get("metrics"), str):
        try:
            feedback["metrics"] = json.loads(feedback["metrics"])
        except json.JSONDecodeError:
            pass
    return feedback


@router.get("/{session_id}/report")
def get_report(session_id: int, user: dict = Depends(get_current_user)):
    state = _load_owned_state(session_id, user)
    generator = ReportGenerator(use_ai=True)
    existing = generator.get_report(session_id)
    if existing:
        return existing
    if not state.answers:
        raise HTTPException(status_code=400, detail="No answers yet; cannot generate report")
    return generator.generate_report(state)


@router.post("/{session_id}/events")
def log_cheat_event(session_id: int, body: CheatEventRequest, user: dict = Depends(get_current_user)):
    _load_owned_state(session_id, user)
    engine = AntiCheatingEngine(session_id=session_id)
    decision = engine.evaluate_event(body.event_type, body.event_data)
    return {
        "accepted": decision is not None,
        "warning": {
            "warning_type": decision.warning_type,
            "message": decision.message,
            "severity": decision.severity,
        }
        if decision
        else None,
    }


def _load_owned_state(session_id: int, user: dict) -> InterviewState:
    state = InterviewSessionService().load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.user_id != user["id"] and user["role"] not in ("admin", "recruiter"):
        raise HTTPException(status_code=403, detail="Not your session")
    return state