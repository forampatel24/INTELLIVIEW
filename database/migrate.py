import os
import re
from datetime import datetime
from typing import Optional

import pymysql

from utils.config import settings


class Database:
    """Creates the database if missing, then applies pending migrations."""

    def __init__(self, host: str = "", port: int = 0, user: str = "", password: str = "", name: str = ""):
        self.host = host or settings.db_host
        self.port = port or settings.db_port
        self.user = user or settings.db_user
        self.password = password if password else settings.db_password
        self.name = name or settings.db_name

    def _server_conn(self) -> pymysql.Connection:
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            charset="utf8mb4",
            autocommit=True,
        )

    def create_database_if_missing(self) -> None:
        conn = self._server_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            conn.close()
        print(f"[db] ensured database `{self.name}` exists")

    def connect(self) -> pymysql.Connection:
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.name,
            charset="utf8mb4",
            autocommit=True,
        )

    def _ensure_migrations_table(self, conn: pymysql.Connection) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    filename   VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _applied(self, conn: pymysql.Connection) -> set[str]:
        with conn.cursor() as cur:
            cur.execute("SELECT filename FROM schema_migrations")
            return {row["filename"] for row in cur.fetchall()}

    def run_migrations(self, migrations_dir: str = "") -> None:
        migrations_dir = migrations_dir or os.path.join(os.path.dirname(__file__), "migrations")
        files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))

        conn = self.connect()
        try:
            self._ensure_migrations_table(conn)
            applied = self._applied(conn)
            for filename in files:
                if filename in applied:
                    continue
                path = os.path.join(migrations_dir, filename)
                with open(path, "r", encoding="utf-8") as fh:
                    script = fh.read()
                self._run_script(conn, script)
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (filename,),
                    )
                print(f"[db] applied migration: {filename}")
        finally:
            conn.close()

    @staticmethod
    def _run_script(conn: pymysql.Connection, script: str) -> None:
        statements = [
            s.strip()
            for s in re.split(r";(?=\s*$)", script, flags=re.MULTILINE)
            if s.strip()
        ]
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)


def migrate() -> None:
    db = Database()
    db.create_database_if_missing()
    db.run_migrations()


if __name__ == "__main__":
    migrate()
