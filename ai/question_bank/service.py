import json
from typing import Optional

from ai.domains import DomainService
from ai.question_bank.definitions import get_bank_entries
from ai.interview_engine.state import Difficulty, QuestionRecord, QuestionType
from database.connection import execute, query


class QuestionBankService:
    """Seeds and queries the per-domain question bank in MySQL.

    Bank questions are stored in the `questions` table with is_ai_generated=FALSE
    and a domain_id. Session questions are is_ai_generated=TRUE and reference a
    session. The two sets are distinguished by those flags.
    """

    def __init__(self):
        self.domains = DomainService()

    # --- Seeding ---

    def seed(self) -> dict:
        inserted = 0
        existing_texts = {
            row["text"] for row in query("SELECT text FROM questions WHERE is_ai_generated = FALSE")
        }
        for entry in get_bank_entries():
            if entry["text"] in existing_texts:
                continue
            domain = self.domains.get_domain(name=entry["domain"])
            domain_id = domain["id"] if domain else None
            execute(
                """
                INSERT INTO questions
                    (domain_id, question_type, difficulty, text, options, correct_answer, skill_tags, is_ai_generated)
                VALUES (%s,%s,%s,%s,%s,%s,%s,FALSE)
                """,
                (
                    domain_id,
                    entry["question_type"],
                    entry["difficulty"],
                    entry["text"],
                    json.dumps(entry["options"]) if entry["options"] else None,
                    entry["correct_answer"],
                    json.dumps(entry["skill_tags"]) if entry["skill_tags"] else None,
                ),
            )
            inserted += 1
        return {"inserted": inserted, "total": len(get_bank_entries())}

    # --- Queries ---

    def count(self) -> int:
        return query("SELECT COUNT(*) AS c FROM questions WHERE is_ai_generated = FALSE")[0]["c"]

    def list_questions(
        self,
        domain_id: Optional[int] = None,
        question_type: Optional[QuestionType] = None,
        difficulty: Optional[Difficulty] = None,
        limit: Optional[int] = None,
    ) -> list[QuestionRecord]:
        clauses = ["is_ai_generated = FALSE"]
        params: list = []
        if domain_id:
            clauses.append("domain_id = %s")
            params.append(domain_id)
        if question_type:
            clauses.append("question_type = %s")
            params.append(question_type.value)
        if difficulty:
            clauses.append("difficulty = %s")
            params.append(difficulty.value)
        sql = "SELECT id, question_type, difficulty, text, options, correct_answer, skill_tags FROM questions WHERE " \
              + " AND ".join(clauses)
        if limit:
            sql += " LIMIT %s"
            params.append(limit)
        return self._rows_to_records(query(sql, tuple(params)))

    def get_random(
        self,
        domain_id: int,
        question_type: QuestionType,
        difficulty: Difficulty,
        exclude_ids: Optional[list[int]] = None,
    ) -> Optional[QuestionRecord]:
        clauses = ["is_ai_generated = FALSE", "domain_id = %s", "question_type = %s", "difficulty = %s"]
        params: list = [domain_id, question_type.value, difficulty.value]
        if exclude_ids:
            placeholders = ",".join(["%s"] * len(exclude_ids))
            clauses.append(f"id NOT IN ({placeholders})")
            params.extend(exclude_ids)
        sql = "SELECT id, question_type, difficulty, text, options, correct_answer, skill_tags FROM questions WHERE " \
              + " AND ".join(clauses) + " ORDER BY RAND() LIMIT 1"
        row = query(sql, tuple(params))
        return self._rows_to_records(row)[0] if row else None

    def by_difficulty_counts(self, domain_id: Optional[int] = None) -> dict:
        clauses = ["is_ai_generated = FALSE"]
        params: list = []
        if domain_id:
            clauses.append("domain_id = %s")
            params.append(domain_id)
        rows = query(
            f"SELECT difficulty, COUNT(*) AS c FROM questions WHERE {' AND '.join(clauses)} GROUP BY difficulty",
            tuple(params),
        )
        return {r["difficulty"]: r["c"] for r in rows}

    @staticmethod
    def _rows_to_records(rows: list[dict]) -> list[QuestionRecord]:
        records = []
        for row in rows:
            records.append(
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
        return records