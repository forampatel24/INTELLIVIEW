"""Face detection using MediaPipe FaceMesh with an OpenCV Haar fallback.

``detect(frame)`` returns a list of ``FaceDetection`` objects. If MediaPipe is
unavailable (or fails to load), the detector falls back to OpenCV's Haar
cascade, which reports bounding boxes only (no landmarks).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    landmarks: Optional[list] = None  # list of normalized landmark stubs
    box: Optional[tuple] = None       # (x, y, w, h) pixel coords
    confidence: Optional[float] = None
    raw: object = None                # MediaPipe face_landmarks

    @property
    def detected(self) -> bool:
        return self.landmarks is not None or self.box is not None


class FaceDetector:
    """Detects faces in a BGR numpy frame.

    MediaPipe FaceMesh returns 468 normalized landmarks. When it is not
    available or fails, OpenCV Haar cascades provide face boxes (no landmarks,
    so attention/eye metrics are unavailable for those detections).
    """

    def __init__(self, max_faces: int = 3, min_detection_confidence: float = 0.5):
        self.max_faces = max_faces
        self.min_detection_confidence = min_detection_confidence
        self._face_mesh = None
        self._haar = None
        self._mediapipe_ok: Optional[bool] = None

    # --- Model loading (lazy) ---

    def _load_face_mesh(self):
        if self._mediapipe_ok is not None:
            return self._face_mesh
        self._mediapipe_ok = False
        try:
            import mediapipe as mp
            import mediapipe.python.solutions.face_mesh as fm
        except Exception as exc:  # pragma: no cover - import env dependent
            logger.warning("MediaPipe unavailable, using Haar fallback: %s", exc)
            return None
        try:
            self._face_mesh = fm.FaceMesh(
                static_image_mode=True,
                max_num_faces=self.max_faces,
                min_detection_confidence=self.min_detection_confidence,
            )
            self._mediapipe_ok = True
        except Exception as exc:  # pragma: no cover - model load env dependent
            logger.warning("FaceMesh init failed, using Haar fallback: %s", exc)
            return None
        return self._face_mesh

    def _load_haar(self):
        if self._haar is not None:
            return self._haar
        import cv2

        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._haar = cv2.CascadeClassifier(cascade)
        return self._haar

    # --- Public API ---

    def detect(self, frame: np.ndarray) -> list[FaceDetection]:
        if frame is None or (hasattr(frame, "size") and frame.size == 0):
            return []
        detections = self._detect_mediapipe(frame)
        if not detections:
            detections = self._detect_haar(frame)
        return detections[: self.max_faces]

    def _detect_mediapipe(self, frame: np.ndarray) -> list[FaceDetection]:
        mesh = self._load_face_mesh()
        if mesh is None:
            return []
        try:
            import cv2

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = mesh.process(rgb)
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.warning("FaceMesh process failed, using Haar fallback: %s", exc)
            self._mediapipe_ok = False
            return []
        detections = []
        if results and results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                detections.append(
                    FaceDetection(
                        landmarks=face_landmarks.landmark,
                        confidence=getattr(results, "face_detections", None),
                        raw=face_landmarks,
                    )
                )
        return detections

    def _detect_haar(self, frame: np.ndarray) -> list[FaceDetection]:
        try:
            import cv2

            cascade = self._load_haar()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        except Exception as exc:  # pragma: no cover - opencv env dependent
            logger.warning("OpenCV Haar detection failed: %s", exc)
            return []
        return [FaceDetection(box=(int(x), int(y), int(w), int(h))) for x, y, w, h in faces]

    def close(self):
        if self._face_mesh is not None:
            try:
                self._face_mesh.close()
            except Exception:  # pragma: no cover
                pass
            self._face_mesh = None
