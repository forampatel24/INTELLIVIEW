import json
from typing import Optional

from ai.interview_engine.state import (
    AnswerRecord,
    Difficulty,
    InterviewState,
    QuestionRecord,
    QuestionType,
    SessionStatus,
)
from database.connection import execute, fetch_one, query


class InterviewSessionService:
    """Persists interview state, questions, and answers to MySQL."""

    # --- Sessions ---

    def create_session(
        self,
        user_id: int,
        mode: str,
        difficulty: Difficulty,
        total_questions: int,
        resume_id: Optional[int] = None,
        domain_id: Optional[int] = None,
        round_type: QuestionType = QuestionType.THEORY,
        focus_skills: Optional[list[str]] = None,
    ) -> InterviewState:
        session_id = execute(
            """
            INSERT INTO interview_sessions
                (user_id, resume_id, domain_id, mode, difficulty, status, total_questions)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                user_id,
                resume_id,
                domain_id,
                mode,
                difficulty.value,
                SessionStatus.PENDING.value,
                total_questions,
            ),
        )
        state = InterviewState(
            session_id=session_id,
            user_id=user_id,
            resume_id=resume_id,
            domain_id=domain_id,
            mode=mode,
            difficulty=difficulty,
            total_questions=total_questions,
            round_type=round_type,
            focus_skills=focus_skills or [],
        )
        return state

    def load_session(self, session_id: int) -> Optional[InterviewState]:
        row = fetch_one(
            "SELECT id, user_id, resume_id, domain_id, mode, difficulty, status, "
            "current_question_index, total_questions FROM interview_sessions WHERE id = %s",
            (session_id,),
        )
        if not row:
            return None
        state = InterviewState(
            session_id=row["id"],
            user_id=row["user_id"],
            resume_id=row["resume_id"],
            domain_id=row["domain_id"],
            mode=row["mode"],
            difficulty=Difficulty(row["difficulty"]),
            status=SessionStatus(row["status"]),
            total_questions=row["total_questions"],
            current_index=row["current_question_index"],
        )
        state.questions = self._load_questions(session_id)
        state.answers = self._load_answers(session_id)
        return state

    def update_status(self, session_id: int, status: SessionStatus) -> None:
        execute("UPDATE interview_sessions SET status = %s WHERE id = %s", (status.value, session_id))

    def update_progress(self, session_id: int, index: int) -> None:
        execute("UPDATE interview_sessions SET current_question_index = %s WHERE id = %s", (index, session_id))

    def mark_started(self, session_id: int) -> None:
        execute("UPDATE interview_sessions SET status = %s, started_at = NOW() WHERE id = %s",
                (SessionStatus.IN_PROGRESS.value, session_id))

    def complete_session(self, session_id: int, overall_score: float) -> None:
        execute(
            "UPDATE interview_sessions SET status = %s, overall_score = %s, ended_at = NOW() "
            "WHERE id = %s",
            (SessionStatus.COMPLETED.value, round(overall_score, 2), session_id),
        )

    # --- Questions ---

    def save_question(self, session_id: int, q: QuestionRecord) -> int:
        return execute(
            """
            INSERT INTO questions
                (session_id, question_type, difficulty, text, options, correct_answer, skill_tags, is_ai_generated)
            VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE)
            """,
            (
                session_id,
                q.question_type.value,
                q.difficulty.value,
                q.text,
                json.dumps(q.options) if q.options else None,
                q.correct_answer,
                json.dumps(q.skill_tags) if q.skill_tags else None,
            ),
        )

    def _load_questions(self, session_id: int) -> list[QuestionRecord]:
        rows = query(
            "SELECT id, question_type, difficulty, text, options, correct_answer, skill_tags "
            "FROM questions WHERE session_id = %s ORDER BY id",
            (session_id,),
        )
        result = []
        for row in rows:
            result.append(
                QuestionRecord(
                    question_id=row["id"],
                    question_type=QuestionType(row["question_type"]),
                    difficulty=Difficulty(row["difficulty"]),
                    text=row["text"],
                    options=json.loads(row["options"]) if row.get("options") else None,
                    correct_answer=row.get("correct_answer"),
                    skill_tags=json.loads(row["skill_tags"]) if row.get("skill_tags") else [],
                )
            )
        return result

    # --- Answers ---

    def save_answer(self, session_id: int, answer: AnswerRecord) -> int:
        return execute(
            """
            INSERT INTO answers
                (session_id, question_id, answer_text, selected_option, code_submitted,
                 time_taken_sec, ai_score, ai_feedback)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                answer_text = VALUES(answer_text),
                selected_option = VALUES(selected_option),
                code_submitted = VALUES(code_submitted),
                time_taken_sec = VALUES(time_taken_sec),
                ai_score = VALUES(ai_score),
                ai_feedback = VALUES(ai_feedback)
            """,
            (
                session_id,
                answer.question.question_id,
                answer.answer_text,
                answer.selected_option,
                answer.code_submitted,
                answer.time_taken_sec,
                answer.ai_score,
                answer.ai_feedback,
            ),
        )

    def _load_answers(self, session_id: int) -> list[AnswerRecord]:
        rows = query(
            "SELECT question_id, answer_text, selected_option, code_submitted, "
            "time_taken_sec, ai_score, ai_feedback FROM answers WHERE session_id = %s ORDER BY id",
            (session_id,),
        )
        question_map = {q.question_id: q for q in self._load_questions(session_id)}
        result = []
        for row in rows:
            q = question_map.get(row["question_id"])
            if not q:
                continue
            result.append(
                AnswerRecord(
                    question=q,
                    answer_text=row.get("answer_text"),
                    selected_option=row.get("selected_option"),
                    code_submitted=row.get("code_submitted"),
                    time_taken_sec=row.get("time_taken_sec") or 0,
                    ai_score=float(row["ai_score"]) if row.get("ai_score") is not None else None,
                    ai_feedback=row.get("ai_feedback"),
                )
            )
        return result