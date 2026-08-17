from typing import Optional

from ai.interview_engine.answer_evaluator import AnswerEvaluator
from ai.interview_engine.difficulty import DifficultySelector
from ai.interview_engine.experience import detect_years_of_experience
from ai.interview_engine.question_generator import QuestionGenerator
from ai.interview_engine.session_service import InterviewSessionService
from ai.interview_engine.state import (
    AnswerRecord,
    Difficulty,
    InterviewState,
    QuestionType,
    SessionStatus,
)
from ai.resume_parser.skill_extractor import SkillExtractor

ROUND_TYPES = [
    QuestionType.THEORY,
    QuestionType.CODING,
    QuestionType.MCQ,
    QuestionType.SCENARIO,
    QuestionType.RAPID_FIRE,
]


class InterviewEngine:
    """Pipeline orchestrator:

    resume -> skill extraction -> experience detection -> difficulty selector
            -> question generator -> state manager -> answer evaluation
            -> adaptive next question -> completion
    """

    def __init__(self, use_ai: bool = True, bank=None):
        self.use_ai = use_ai
        self.session_service = InterviewSessionService()
        self.difficulty_selector = DifficultySelector()
        self.question_generator = QuestionGenerator(use_ai=use_ai, bank=bank)
        self.answer_evaluator = AnswerEvaluator(use_ai=use_ai)
        self.skill_extractor = SkillExtractor()

    # --- Session lifecycle ---

    def start_session(
        self,
        user_id: int,
        mode: str = "resume",
        total_questions: int = 5,
        resume_data: Optional[dict] = None,
        resume_id: Optional[int] = None,
        domain_id: Optional[int] = None,
        round_type: QuestionType = QuestionType.THEORY,
        focus_skills: Optional[list[str]] = None,
    ) -> InterviewState:
        skills = focus_skills or self._extract_skills(resume_data, mode)
        years = detect_years_of_experience(resume_data or {})
        difficulty = self.difficulty_selector.initial_difficulty(years)
        state = self.session_service.create_session(
            user_id=user_id,
            mode=mode,
            difficulty=difficulty,
            total_questions=total_questions,
            resume_id=resume_id,
            domain_id=domain_id,
            round_type=round_type,
            focus_skills=skills,
        )
        self.session_service.mark_started(state.session_id)
        return state

    # --- Question flow ---

    def get_current_question(self, state: InterviewState) -> dict:
        """Generates and persists the current question if not yet asked."""
        if state.current_index >= len(state.questions):
            asked_texts = [q.text for q in state.questions]
            question = self.question_generator.generate(
                state.round_type,
                state.difficulty,
                state.focus_skills,
                asked_texts=asked_texts,
                domain_id=state.domain_id,
            )
            question.question_id = self.session_service.save_question(state.session_id, question)
            state.questions.append(question)
        question = state.questions[state.current_index]
        return {
            "index": state.current_index,
            "total": state.total_questions,
            "question_id": question.question_id,
            "type": question.question_type.value,
            "difficulty": question.difficulty.value,
            "text": question.text,
            "options": question.options,
            "skill_tags": question.skill_tags,
        }

    def submit_answer(
        self,
        state: InterviewState,
        answer_text: Optional[str] = None,
        selected_option: Optional[str] = None,
        code_submitted: Optional[str] = None,
        time_taken_sec: int = 0,
    ) -> dict:
        if state.is_complete:
            raise ValueError("Interview already complete")
        if state.current_index >= len(state.questions):
            # Question not yet requested — generate it so the flow is forgiving.
            question = self.question_generator.generate(
                state.round_type,
                state.difficulty,
                state.focus_skills,
                asked_texts=[q.text for q in state.questions],
                domain_id=state.domain_id,
            )
            question.question_id = self.session_service.save_question(state.session_id, question)
            state.questions.append(question)
        question = state.questions[state.current_index]
        answer = AnswerRecord(
            question=question,
            answer_text=answer_text,
            selected_option=selected_option,
            code_submitted=code_submitted,
            time_taken_sec=time_taken_sec,
        )
        answer = self.answer_evaluator.evaluate(question, answer)
        self.session_service.save_answer(state.session_id, answer)
        state.answers.append(answer)
        state.current_index += 1
        self.session_service.update_progress(state.session_id, state.current_index)
        state.difficulty = self.difficulty_selector.next_difficulty(
            state.difficulty, [a.ai_score for a in state.answers]
        )
        return {
            "score": answer.ai_score,
            "feedback": answer.ai_feedback,
            "next_difficulty": state.difficulty.value,
            "is_complete": state.is_complete,
        }

    def next_question(self, state: InterviewState) -> dict:
        if state.is_complete:
            overall = self._overall_score(state)
            self.session_service.complete_session(state.session_id, overall)
            state.status = SessionStatus.COMPLETED
            return {
                "is_complete": True,
                "overall_score": round(overall, 2),
                "state": state.state_dict,
            }
        return self.get_current_question(state)

    # --- Helpers ---

    def _extract_skills(self, resume_data: Optional[dict], mode: str) -> list[str]:
        if resume_data and resume_data.get("skills"):
            return resume_data["skills"]
        if resume_data and resume_data.get("sections"):
            return self.skill_extractor.extract_from_sections(resume_data["sections"])
        return ["Python", "SQL"] if mode == "domain" else []

    @staticmethod
    def _overall_score(state: InterviewState) -> float:
        scores = [a.ai_score for a in state.answers if a.ai_score is not None]
        return sum(scores) / len(scores) if scores else 0.0