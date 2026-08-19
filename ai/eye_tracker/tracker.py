"""Eye tracker — focused gaze/blink analysis for the eye_tracking table.

Reuses FaceDetector + geometry to compute gaze offsets, eye contact, and
blink-derived signals, exposed as a small standalone package.
"""

from typing import Optional

import numpy as np

from ai.face_monitor.detector import FaceDetector
from ai.face_monitor import geometry


class EyeTracker:
    """Computes per-frame eye metrics for a BGR frame."""

    def __init__(self, detector: Optional[FaceDetector] = None):
        self.detector = detector or FaceDetector()

    def track(self, frame: np.ndarray) -> dict:
        detections = self.detector.detect(frame)
        if not detections:
            return {
                "face_detected": False,
                "gaze_x": None,
                "gaze_y": None,
                "eye_contact": None,
                "looking_away": None,
                "drowsy": None,
                "blink_rate": None,
            }
        primary = max(detections, key=lambda d: (d.box[2] * d.box[3] if d.box else 0))
        lm = primary.landmarks
        if lm is None:
            return {
                "face_detected": True,
                "gaze_x": None,
                "gaze_y": None,
                "eye_contact": None,
                "looking_away": None,
                "drowsy": None,
                "blink_rate": None,
            }
        return {
            "face_detected": True,
            "gaze_x": geometry.gaze_offset_x(lm),
            "gaze_y": geometry.gaze_offset_y(lm),
            "eye_contact": geometry.eye_contact(lm),
            "looking_away": geometry.looking_away(lm),
            "drowsy": geometry.is_drowsy(lm),
            "blink_rate": None,
        }