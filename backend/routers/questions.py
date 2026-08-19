"""Question bank listing endpoints (phase 15)."""

from typing import Optional

from fastapi import APIRouter, Depends

from ai.interview_engine.state import Difficulty, QuestionType
from ai.question_bank import QuestionBankService
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("")
def list_questions(
    domain_id: Optional[int] = None,
    question_type: Optional[QuestionType] = None,
    difficulty: Optional[Difficulty] = None,
    limit: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    records = QuestionBankService().list_questions(
        domain_id=domain_id,
        question_type=question_type,
        difficulty=difficulty,
        limit=limit,
    )
    return [
        {
            "question_id": r.question_id,
            "type": r.question_type.value,
            "difficulty": r.difficulty.value,
            "text": r.text,
            "options": r.options,
            "skill_tags": r.skill_tags,
        }
        for r in records
    ]


@router.get("/counts")
def question_counts(
    domain_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    return QuestionBankService().by_difficulty_counts(domain_id=domain_id)