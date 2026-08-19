"""Frame analyzer: converts a camera frame into a CameraSnapshot.

The snapshot mirrors the ``camera_logs`` and ``eye_tracking`` tables so it can
be persisted directly by CameraMonitoringService.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ai.face_monitor.detector import FaceDetector
from ai.face_monitor import geometry


@dataclass
class CameraSnapshot:
    face_detected: bool = False
    face_count: int = 0
    attention_score: Optional[float] = None
    eye_contact: Optional[bool] = None
    looking_away: Optional[bool] = None
    head_movement: Optional[float] = None
    drowsy: bool = False
    smile_detected: bool = False
    confidence: Optional[float] = None
    gaze_x: Optional[float] = None
    gaze_y: Optional[float] = None
    blink_rate: Optional[float] = None
    extra: dict = field(default_factory=dict)

    def to_db_row(self) -> dict:
        return {
            "face_detected": self.face_detected,
            "face_count": self.face_count,
            "attention_score": self.attention_score,
            "eye_contact": self.eye_contact,
            "looking_away": self.looking_away,
            "head_movement": self.head_movement,
            "drowsy": self.drowsy,
            "smile_detected": self.smile_detected,
            "confidence": self.confidence,
        }


class FrameAnalyzer:
    """Analyzes a single BGR frame and produces a CameraSnapshot."""

    def __init__(self, detector: Optional[FaceDetector] = None):
        self.detector = detector or FaceDetector()

    def analyze(self, frame: np.ndarray) -> CameraSnapshot:
        if frame is None or (hasattr(frame, "size") and frame.size == 0):
            return CameraSnapshot(face_detected=False, face_count=0)

        detections = self.detector.detect(frame)
        if not detections:
            return CameraSnapshot(face_detected=False, face_count=0)

        snap = CameraSnapshot(face_detected=True, face_count=len(detections))
        # Analyze the largest detection (highest confidence / biggest box).
        primary = max(detections, key=lambda d: (d.confidence is not None, d.box[2] * d.box[3] if d.box else 0))
        lm = primary.landmarks
        if lm is not None:
            left_ear = geometry.eye_aspect_ratio(lm, geometry.EAR_LEFT)
            right_ear = geometry.eye_aspect_ratio(lm, geometry.EAR_RIGHT)
            snap.eye_contact = geometry.eye_contact(lm)
            snap.looking_away = geometry.looking_away(lm)
            snap.head_movement = geometry.head_movement(lm)
            snap.gaze_x = geometry.gaze_offset_x(lm)
            snap.gaze_y = geometry.gaze_offset_y(lm)
            snap.drowsy = bool(geometry.is_drowsy(lm))
            mar = geometry.mouth_aspect_ratio(lm)
            snap.smile_detected = bool(mar is not None and mar > 0.35)
            snap.confidence = primary.confidence if primary.confidence is not None else self._confidence(left_ear, right_ear)
            snap.attention_score = self._attention_score(snap, left_ear, right_ear)
        else:
            # Haar-only detection: no landmark-derived signals available.
            snap.confidence = primary.confidence if primary.confidence is not None else 1.0
            snap.attention_score = 100.0
        return snap

    @staticmethod
    def _confidence(left_ear: Optional[float], right_ear: Optional[float]) -> float:
        if left_ear is None or right_ear is None:
            return 0.5
        return round(min(1.0, max(0.0, (left_ear + right_ear) / 2.0 / 0.4)), 2)

    @staticmethod
    def _attention_score(snap: CameraSnapshot, left_ear: Optional[float], right_ear: Optional[float]) -> float:
        score = 100.0
        if snap.eye_contact is False:
            score -= 20
        if snap.looking_away:
            score -= 25
        if snap.head_movement is not None:
            score -= int(snap.head_movement * 30)
        if snap.drowsy:
            score -= 40
        if snap.smile_detected:
            score += 5
        return round(max(0.0, min(100.0, score)), 2)