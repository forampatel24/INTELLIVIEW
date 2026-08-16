import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, Enum):
    MCQ = "mcq"
    CODING = "coding"
    THEORY = "theory"
    SCENARIO = "scenario"
    RAPID_FIRE = "rapid_fire"


class SessionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"


DIFFICULTY_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]


@dataclass
class QuestionRecord:
    question_type: QuestionType
    difficulty: Difficulty
    text: str
    options: Optional[list[str]] = None
    correct_answer: Optional[str] = None
    skill_tags: list[str] = field(default_factory=list)
    question_id: Optional[int] = None


@dataclass
class AnswerRecord:
    question: QuestionRecord
    answer_text: Optional[str] = None
    selected_option: Optional[str] = None
    code_submitted: Optional[str] = None
    time_taken_sec: int = 0
    ai_score: Optional[float] = None
    ai_feedback: Optional[str] = None


@dataclass
class InterviewState:
    """In-memory state for one interview session."""

    session_id: Optional[int] = None
    user_id: Optional[int] = None
    resume_id: Optional[int] = None
    domain_id: Optional[int] = None
    mode: str = "resume"
    difficulty: Difficulty = Difficulty.MEDIUM
    status: SessionStatus = SessionStatus.PENDING
    total_questions: int = 5
    current_index: int = 0
    questions: list[QuestionRecord] = field(default_factory=list)
    answers: list[AnswerRecord] = field(default_factory=list)
    round_type: QuestionType = QuestionType.THEORY
    focus_skills: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.current_index >= self.total_questions

    @property
    def last_score(self) -> Optional[float]:
        if not self.answers:
            return None
        scores = [a.ai_score for a in self.answers if a.ai_score is not None]
        return scores[-1] if scores else None

    @property
    def average_score(self) -> float:
        scores = [a.ai_score for a in self.answers if a.ai_score is not None]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def state_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "difficulty": self.difficulty.value,
            "status": self.status.value,
            "current_index": self.current_index,
            "total_questions": self.total_questions,
            "round_type": self.round_type.value,
            "focus_skills": self.focus_skills,
            "average_score": round(self.average_score, 2),
            "last_score": self.last_score,
            "is_complete": self.is_complete,
        }