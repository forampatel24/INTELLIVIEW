"""Persistence and reads for camera monitoring data.

Writes snapshots to ``camera_logs``, eye data to ``eye_tracking``, raises
warnings to ``warnings``, and records activity/analytics events.
"""

import json
from typing import Optional

from ai.face_monitor.analyzer import CameraSnapshot
from database.connection import execute, fetch_one, query


class CameraMonitoringService:
    """Stores camera/eye-tracking observations for an interview session."""

    # --- Writes ---

    def log_snapshot(self, session_id: int, snapshot: CameraSnapshot) -> int:
        row = snapshot.to_db_row()
        return execute(
            """
            INSERT INTO camera_logs
                (session_id, face_detected, face_count, attention_score, eye_contact,
                 looking_away, head_movement, drowsy, smile_detected, confidence)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                session_id,
                row["face_detected"],
                row["face_count"],
                row["attention_score"],
                row["eye_contact"],
                row["looking_away"],
                row["head_movement"],
                row["drowsy"],
                row["smile_detected"],
                row["confidence"],
            ),
        )

    def log_eye(self, session_id: int, snapshot: CameraSnapshot) -> int:
        return execute(
            """
            INSERT INTO eye_tracking (session_id, gaze_x, gaze_y, eye_contact, blink_rate)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                session_id,
                snapshot.gaze_x,
                snapshot.gaze_y,
                snapshot.eye_contact,
                snapshot.blink_rate,
            ),
        )

    def log_warning(
        self,
        session_id: int,
        warning_type: str,
        message: str,
        severity: str = "medium",
    ) -> int:
        return execute(
            """
            INSERT INTO warnings (session_id, warning_type, severity, message)
            VALUES (%s,%s,%s,%s)
            """,
            (session_id, warning_type, severity, message),
        )

    def log_activity(
        self,
        session_id: int,
        event_type: str,
        event_data: Optional[dict] = None,
        severity: str = "info",
    ) -> int:
        return execute(
            """
            INSERT INTO activity_logs (session_id, event_type, event_data, severity)
            VALUES (%s,%s,%s,%s)
            """,
            (session_id, event_type, json.dumps(event_data) if event_data else None, severity),
        )

    def record_analytics(
        self,
        user_id: int,
        metric_name: str,
        metric_value: Optional[float] = None,
        metric_data: Optional[dict] = None,
        session_id: Optional[int] = None,
    ) -> int:
        return execute(
            """
            INSERT INTO analytics (user_id, session_id, metric_name, metric_value, metric_data)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (user_id, session_id, metric_name, metric_value, json.dumps(metric_data) if metric_data else None),
        )

    # --- Reads ---

    def get_camera_logs(self, session_id: int, limit: int = 200) -> list[dict]:
        return query(
            "SELECT * FROM camera_logs WHERE session_id = %s ORDER BY timestamp DESC LIMIT %s",
            (session_id, limit),
        )

    def get_eye_tracking(self, session_id: int, limit: int = 200) -> list[dict]:
        return query(
            "SELECT * FROM eye_tracking WHERE session_id = %s ORDER BY timestamp DESC LIMIT %s",
            (session_id, limit),
        )

    def get_warnings(self, session_id: int) -> list[dict]:
        return query(
            "SELECT * FROM warnings WHERE session_id = %s ORDER BY occurred_at DESC",
            (session_id,),
        )

    def get_activity_logs(self, session_id: int, limit: int = 200) -> list[dict]:
        return query(
            "SELECT * FROM activity_logs WHERE session_id = %s ORDER BY created_at DESC LIMIT %s",
            (session_id, limit),
        )

    def get_analytics(self, user_id: Optional[int] = None, metric_name: Optional[str] = None) -> list[dict]:
        if user_id is not None and metric_name is not None:
            return query(
                "SELECT * FROM analytics WHERE user_id = %s AND metric_name = %s ORDER BY recorded_at DESC",
                (user_id, metric_name),
            )
        if user_id is not None:
            return query(
                "SELECT * FROM analytics WHERE user_id = %s ORDER BY recorded_at DESC",
                (user_id,),
            )
        return query("SELECT * FROM analytics ORDER BY recorded_at DESC")

    # --- Summary ---

    def session_summary(self, session_id: int) -> dict:
        cam = query(
            "SELECT COUNT(*) AS total, SUM(face_detected) AS faces, "
            "AVG(attention_score) AS avg_attention, AVG(head_movement) AS avg_head_movement "
            "FROM camera_logs WHERE session_id = %s",
            (session_id,),
        )
        eye = query(
            "SELECT AVG(blink_rate) AS avg_blink_rate, COUNT(eye_contact) AS eye_samples "
            "FROM eye_tracking WHERE session_id = %s",
            (session_id,),
        )
        warn = query(
            "SELECT COUNT(*) AS total FROM warnings WHERE session_id = %s",
            (session_id,),
        )
        c = cam[0] if cam else {}
        e = eye[0] if eye else {}
        w = warn[0] if warn else {}
        return {
            "session_id": session_id,
            "camera_samples": int(c.get("total") or 0),
            "face_detected_samples": int(c.get("faces") or 0),
            "avg_attention_score": round(float(c["avg_attention"]), 2) if c.get("avg_attention") is not None else None,
            "avg_head_movement": round(float(c["avg_head_movement"]), 2) if c.get("avg_head_movement") is not None else None,
            "avg_blink_rate": round(float(e["avg_blink_rate"]), 2) if e.get("avg_blink_rate") is not None else None,
            "eye_samples": int(e.get("eye_samples") or 0),
            "warning_count": int(w.get("total") or 0),
        }

    def session_warning_summary(self, session_id: int) -> dict:
        rows = query(
            "SELECT warning_type, COUNT(*) AS cnt FROM warnings "
            "WHERE session_id = %s GROUP BY warning_type ORDER BY cnt DESC",
            (session_id,),
        )
        return {r["warning_type"]: int(r["cnt"]) for r in rows}