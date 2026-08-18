"""Builds structured report data (charts, strengths, resources) from a session.

All builders are pure functions over an InterviewState and the FeedbackMetrics
dict so they are easy to unit-test and reuse from both AI and heuristic paths.
"""

from typing import Optional

from ai.interview_engine.state import Difficulty, InterviewState, QuestionType

MAX_RADAR_SKILLS = 6
MAX_RESOURCES = 5

# Curated learning resources keyed by lowercase skill name.
RESOURCE_MAP = {
    "python": "https://docs.python.org/3/tutorial/",
    "python programming": "https://docs.python.org/3/tutorial/",
    "c++": "https://www.learncpp.com/",
    "java": "https://docs.oracle.com/javase/tutorial/",
    "javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "react": "https://react.dev/learn",
    "node.js": "https://nodejs.org/en/learn",
    "nodejs": "https://nodejs.org/en/learn",
    "express": "https://expressjs.com/",
    "sql": "https://www.w3schools.com/sql/",
    "dbms": "https://www.javatpoint.com/dbms-tutorial",
    "data structures": "https://www.geeksforgeeks.org/data-structures/",
    "algorithms": "https://www.geeksforgeeks.org/fundamentals-of-algorithms/",
    "operating systems": "https://www.geeksforgeeks.org/operating-systems/",
    "computer networks": "https://www.geeksforgeeks.org/computer-network-tutorials/",
    "machine learning": "https://www.coursera.org/learn/machine-learning",
    "deep learning": "https://www.coursera.org/specializations/deep-learning",
    "system design": "https://github.com/donnemartin/system-design-primer",
    "cloud computing": "https://aws.amazon.com/training/",
    "aws": "https://aws.amazon.com/training/",
    "devops": "https://www.docker.com/101-tutorial/",
    "docker": "https://www.docker.com/101-tutorial/",
    "kubernetes": "https://kubernetes.io/docs/tutorials/",
    "linux": "https://linuxjourney.com/",
    "communication": "https://www.coursera.org/learn/wharton-communication-skills",
    "problem solving": "https://leetcode.com/",
    "behavioral": "https://www.themuse.com/advice/star-interview-method",
}


def build_radar_data(state: InterviewState, metrics: dict) -> list[dict]:
    """Top skills with scores — suitable for a radar/bar chart."""
    skills = metrics.get("skills") or {}
    radar = [{"skill": skill, "score": round(score, 2)} for skill, score in skills.items()]
    radar = radar[:MAX_RADAR_SKILLS]
    # Ensure at least 3 axes so radar charts render nicely.
    if len(radar) < 3:
        radar.append({"skill": "Overall", "score": round(metrics.get("overall_score", 0), 2)})
    if len(radar) < 3:
        for t in QuestionType:
            by_type = metrics.get("by_type", {}).get(t.value)
            if by_type and len(radar) < 3:
                radar.append({"skill": t.value.replace("_", " ").title(), "score": by_type.get("avg_score", 0)})
    return radar


def build_heatmap_data(state: InterviewState, metrics: dict) -> dict:
    """Avg score per (difficulty, question_type) cell — for a heatmap."""
    difficulty_order = [d.value for d in Difficulty]
    type_order = [t.value for t in QuestionType]
    cells: dict[tuple[str, str], list[float]] = {}
    for a in state.answers:
        if a.ai_score is None:
            continue
        key = (a.question.difficulty.value, a.question.question_type.value)
        cells.setdefault(key, []).append(a.ai_score)

    values = []
    for d in difficulty_order:
        row = []
        for t in type_order:
            scores = cells.get((d, t))
            row.append(round(sum(scores) / len(scores), 2) if scores else None)
        values.append(row)
    return {
        "difficulties": difficulty_order,
        "question_types": type_order,
        "values": values,
    }


def build_timeline_data(state: InterviewState, metrics: dict) -> list[dict]:
    """Score per answered question, in order — for a line chart."""
    timeline = []
    for idx, a in enumerate(state.answers, start=1):
        timeline.append(
            {
                "index": idx,
                "score": a.ai_score,
                "difficulty": a.question.difficulty.value,
                "type": a.question.question_type.value,
            }
        )
    return timeline


def build_strengths(metrics: dict) -> list[str]:
    strengths = []
    if metrics.get("mcq", {}).get("accuracy") is not None and metrics["mcq"]["accuracy"] >= 0.7:
        strengths.append("Strong MCQ accuracy")
    if metrics.get("overall_score", 0) >= 70:
        strengths.append("Good overall performance")
    top_skills = list((metrics.get("skills") or {}).items())[:2]
    strengths.extend(f"Strong in {skill}" for skill, score in top_skills if score >= 70)
    return strengths[:3] or ["Consistent participation"]


def build_weaknesses(metrics: dict) -> list[str]:
    weaknesses = []
    low_skills = [(s, sc) for s, sc in (metrics.get("skills") or {}).items() if sc < 60]
    weaknesses.extend(f"Needs improvement in {skill}" for skill, _ in low_skills[:2])
    if metrics.get("unanswered", 0) > 0:
        weaknesses.append(f"{metrics['unanswered']} questions unanswered")
    return weaknesses[:3] or ["Deeper practice recommended"]


def build_suggestions(metrics: dict, weaknesses: list[str]) -> list[str]:
    suggestions = []
    low_skills = [s for s, sc in (metrics.get("skills") or {}).items() if sc < 60]
    suggestions.extend(
        f"Revisit {skill} fundamentals" for skill in low_skills[:2] if skill not in suggestions
    )
    if metrics.get("unanswered", 0) > 0:
        suggestions.append("Manage time to attempt every question")
    if metrics.get("avg_time_per_question_sec", 0) > 120:
        suggestions.append("Work on answering questions faster")
    return (suggestions[:3] if suggestions else ["Continue practicing with mock interviews"])


def build_learning_resources(weaknesses: list[str], metrics: dict) -> list[dict]:
    """Maps weak skill areas to curated learning resources."""
    topics: list[str] = []
    for skill, score in (metrics.get("skills") or {}).items():
        if score < 70 and skill.lower() not in topics:
            topics.append(skill.lower())
    # Fall back to weaknesses phrasing if no weak skills were tagged.
    for w in weaknesses:
        topic = w.replace("Needs improvement in ", "").strip().lower()
        if topic and topic not in topics:
            topics.append(topic)

    resources = []
    for topic in topics[:MAX_RESOURCES]:
        url = RESOURCE_MAP.get(topic)
        if url:
            resources.append({"topic": topic, "resource": url})
    if not resources:
        resources.append(
            {
                "topic": "interview preparation",
                "resource": "https://www.indeed.com/career-advice/interviewing/interview-questions-and-answers",
            }
        )
    return resources


def build_recruiter_summary(metrics: dict, recommendation: str, strengths: list[str]) -> str:
    overall = metrics.get("overall_score", 0)
    total = metrics.get("total_questions", 0)
    strength_text = ", ".join(strengths[:2]) or "steady performance"
    return (
        f"Candidate scored {overall:.0f}/100 across {total} questions. "
        f"Notable areas: {strength_text}. "
        f"Recommendation: {recommendation.upper()}."
    )
