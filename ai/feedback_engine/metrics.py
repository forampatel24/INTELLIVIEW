from typing import Optional

from ai.interview_engine.state import AnswerRecord, Difficulty, InterviewState


class FeedbackMetrics:
    """Computes structured metrics from a completed interview session."""

    @staticmethod
    def compute(state: InterviewState) -> dict:
        answers = state.answers
        scored = [a for a in answers if a.ai_score is not None]
        overall = sum(a.ai_score for a in scored) / len(scored) if scored else 0.0

        # Per-difficulty performance
        by_difficulty: dict[str, dict] = {}
        for difficulty in Difficulty:
            d_answers = [a for a in scored if a.question.difficulty == difficulty]
            if d_answers:
                by_difficulty[difficulty.value] = {
                    "count": len(d_answers),
                    "avg_score": round(sum(a.ai_score for a in d_answers) / len(d_answers), 2),
                }

        # Per-question-type performance
        by_type: dict[str, dict] = {}
        for a in scored:
            key = a.question.question_type.value
            bucket = by_type.setdefault(key, {"count": 0, "total": 0.0, "avg_score": 0.0})
            bucket["count"] += 1
            bucket["total"] += a.ai_score
        for bucket in by_type.values():
            bucket["avg_score"] = round(bucket["total"] / bucket["count"], 2)

        # Skill-level breakdown (skill_tags on each question)
        skill_scores: dict[str, list[float]] = {}
        for a in scored:
            for tag in (a.question.skill_tags or [])[:2]:
                skill_scores.setdefault(tag, []).append(a.ai_score)
        skills = {
            skill: round(sum(scores) / len(scores), 2)
            for skill, scores in sorted(skill_scores.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
        }

        # Answer coverage
        answered = len(answers)
        mcq_answers = [a for a in answers if a.question.question_type.value == "mcq" and a.selected_option]
        mcq_correct = sum(
            1
            for a in mcq_answers
            if a.question.correct_answer
            and (a.selected_option or "").strip().upper() == a.question.correct_answer.strip().upper()
        )

        avg_time = (
            sum(a.time_taken_sec for a in answers) / len(answers) if answers else 0
        )

        # Difficulty adaptation path (did the engine escalate/descalate?)
        difficulty_path = [state.difficulty.value]  # initial
        if state.questions:
            difficulty_path = [q.difficulty.value for q in state.questions]

        return {
            "overall_score": round(overall, 2),
            "total_questions": len(answers),
            "answered": answered,
            "unanswered": max(0, state.total_questions - answered),
            "avg_time_per_question_sec": round(avg_time, 1),
            "by_difficulty": by_difficulty,
            "by_type": by_type,
            "skills": skills,
            "mcq": {
                "total": len(mcq_answers),
                "correct": mcq_correct,
                "accuracy": round(mcq_correct / len(mcq_answers), 2) if mcq_answers else None,
            },
            "difficulty_path": difficulty_path,
            "consistency": FeedbackMetrics._consistency(scored),
        }

    @staticmethod
    def _consistency(scored: list[AnswerRecord]) -> float:
        """Standard deviation-based consistency: higher = more consistent."""
        if len(scored) < 2:
            return 0.0
        scores = [a.ai_score for a in scored]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return round(100.0 - min(100.0, variance ** 0.5), 2)