import queue
import threading
from typing import Any, Optional

import pymysql
from pymysql.cursors import DictCursor

from utils.config import settings


class ConnectionPool:
    """Thread-safe MySQL connection pool using PyMySQL (no ORM)."""

    def __init__(self, max_connections: int = 10):
        self._max = max_connections
        self._idle: queue.Queue = queue.Queue(maxsize=max_connections)
        self._active = 0
        self._lock = threading.Lock()
        self._local = threading.local()

    def _create(self) -> pymysql.Connection:
        return pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
        )

    def acquire(self) -> pymysql.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is not None and self._is_alive(conn):
            return conn
        try:
            conn = self._idle.get_nowait()
        except queue.Empty:
            with self._lock:
                if self._active < self._max:
                    self._active += 1
                    conn = self._create()
                else:
                    conn = self._idle.get(timeout=10)
        self._local.conn = conn
        return conn

    def release(self, conn: Optional[pymysql.Connection] = None) -> None:
        conn = conn or getattr(self._local, "conn", None)
        if conn is None:
            return
        self._local.conn = None
        try:
            if self._is_alive(conn):
                self._idle.put_nowait(conn)
            else:
                with self._lock:
                    self._active = max(0, self._active - 1)
        except queue.Full:
            with self._lock:
                self._active = max(0, self._active - 1)

    @staticmethod
    def _is_alive(conn: pymysql.Connection) -> bool:
        try:
            conn.ping(reconnect=True)
            return True
        except Exception:
            return False


_pool = ConnectionPool()


def get_conn() -> pymysql.Connection:
    return _pool.acquire()


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        _pool.release(conn)


def execute(sql: str, params: tuple = ()) -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid
    finally:
        _pool.release(conn)


def execute_many(sql: str, rows: list[tuple]) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
    finally:
        _pool.release(conn)


def fetch_one(sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
    rows = query(sql, params)
    return rows[0] if rows else None
