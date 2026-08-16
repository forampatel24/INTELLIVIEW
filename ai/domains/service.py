import json
from typing import Optional

from ai.domains.definitions import CATEGORIES, DOMAINS
from database.connection import execute, fetch_one, query


class DomainService:
    """CRUD + seeding for the domains table."""

    # --- Seeding ---

    def seed(self) -> dict:
        """Insert any missing predefined domains. Idempotent."""
        inserted = 0
        existing = {row["name"] for row in query("SELECT name FROM domains")}
        for name, category, description, focus_skills in DOMAINS:
            if name in existing:
                continue
            execute(
                "INSERT INTO domains (name, category, description, focus_skills) VALUES (%s,%s,%s,%s)",
                (name, category, description, json.dumps(focus_skills)),
            )
            inserted += 1
        return {"inserted": inserted, "total": len(DOMAINS)}

    # --- Reads ---

    def list_domains(self, category: Optional[str] = None, active_only: bool = True) -> list[dict]:
        sql = "SELECT id, name, category, description, focus_skills, is_active FROM domains"
        params: list = []
        clauses: list[str] = []
        if category:
            clauses.append("category = %s")
            params.append(category)
        if active_only:
            clauses.append("is_active = TRUE")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY category, name"
        rows = query(sql, tuple(params))
        for row in rows:
            row["focus_skills"] = json.loads(row["focus_skills"]) if row.get("focus_skills") else []
        return rows

    def list_categories(self) -> list[str]:
        return [row["category"] for row in query("SELECT DISTINCT category FROM domains ORDER BY category")]

    def get_domain(self, domain_id: Optional[int] = None, name: Optional[str] = None) -> Optional[dict]:
        if domain_id:
            row = fetch_one("SELECT * FROM domains WHERE id = %s", (domain_id,))
        elif name:
            row = fetch_one("SELECT * FROM domains WHERE name = %s", (name,))
        else:
            return None
        if not row:
            return None
        row["focus_skills"] = json.loads(row["focus_skills"]) if row.get("focus_skills") else []
        return row

    def get_by_names(self, names: list[str]) -> list[dict]:
        if not names:
            return []
        placeholders = ",".join(["%s"] * len(names))
        rows = query(f"SELECT id, name, category, focus_skills FROM domains WHERE name IN ({placeholders})", tuple(names))
        for row in rows:
            row["focus_skills"] = json.loads(row["focus_skills"]) if row.get("focus_skills") else []
        return rows

    # --- Writes ---

    def create_domain(self, name: str, category: str, description: Optional[str] = None,
                      focus_skills: Optional[list[str]] = None) -> int:
        if self.get_domain(name=name):
            raise ValueError(f"Domain already exists: {name}")
        return execute(
            "INSERT INTO domains (name, category, description, focus_skills) VALUES (%s,%s,%s,%s)",
            (name, category, description, json.dumps(focus_skills or [])),
        )

    def set_active(self, domain_id: int, is_active: bool) -> None:
        execute("UPDATE domains SET is_active = %s WHERE id = %s", (is_active, domain_id))