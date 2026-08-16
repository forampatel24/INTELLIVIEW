from typing import Optional

from ai.interview_engine.state import DIFFICULTY_ORDER, Difficulty


class DifficultySelector:
    """Adaptively adjusts question difficulty based on recent performance.

    Rule: after each answer, move toward the difficulty whose band the
    recent average score falls into. Streaks of weak answers pull down
    faster than one good answer pushes up.
    """

    WINDOW = 3  # look at last N answers
    BANDS = {
        Difficulty.EASY: (0, 45),
        Difficulty.MEDIUM: (45, 75),
        Difficulty.HARD: (75, 101),
    }

    def next_difficulty(self, current: Difficulty, recent_scores: list[Optional[float]]) -> Difficulty:
        scores = [s for s in recent_scores[-self.WINDOW:] if s is not None]
        if not scores:
            return current
        avg = sum(scores) / len(scores)

        for difficulty, (lo, hi) in self.BANDS.items():
            if lo <= avg < hi:
                target = difficulty

        current_pos = DIFFICULTY_ORDER.index(current)
        target_pos = DIFFICULTY_ORDER.index(target)
        # Slight hysteresis: move at most one step per answer.
        if target_pos > current_pos:
            return DIFFICULTY_ORDER[current_pos + 1] if current_pos < len(DIFFICULTY_ORDER) - 1 else target
        if target_pos < current_pos:
            return DIFFICULTY_ORDER[current_pos - 1] if current_pos > 0 else target
        return current

    @staticmethod
    def initial_difficulty(years_of_experience: float) -> Difficulty:
        if years_of_experience >= 4:
            return Difficulty.HARD
        if years_of_experience >= 1:
            return Difficulty.MEDIUM
        return Difficulty.EASY