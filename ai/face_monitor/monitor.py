"""CameraMonitor — drives a camera/video source, analyzes frames, persists.

The source is any iterable of BGR frames (list, generator, cv2.VideoCapture).
``start`` consumes frames until the source ends or ``stop`` is called, so it
works both with a real webcam and with test frame feeds.
"""

import time
from collections import deque
from typing import Callable, Iterable, Optional

import numpy as np

from ai.face_monitor.analyzer import CameraSnapshot, FrameAnalyzer
from ai.face_monitor.service import CameraMonitoringService

FrameSource = Iterable[Optional[np.ndarray]]


class CameraMonitor:
    """Analyzes and logs camera frames for an interview session.

    Frames are analyzed and logged at most every ``log_interval_sec`` seconds
    (snapshot + eye tracking each once per interval). ``on_warning`` is called
    for rule triggers — the anti-cheating module (phase 12) will supply rules.
    """

    def __init__(
        self,
        session_id: Optional[int] = None,
        analyzer: Optional[FrameAnalyzer] = None,
        service: Optional[CameraMonitoringService] = None,
        log_interval_sec: float = 1.0,
        on_warning: Optional[Callable[[int, str, str, str], None]] = None,
    ):
        self.session_id = session_id
        self.analyzer = analyzer or FrameAnalyzer()
        self.service = service or CameraMonitoringService()
        self.log_interval_sec = log_interval_sec
        self.on_warning = on_warning
        self._last_log_time = 0.0
        self._running = False
        self._frames_processed = 0
        self._snapshots_logged = 0
        self._eye_logged = 0
        self._last_ear = deque(maxlen=30)
        self._blink_count = 0
        self._last_blink_time = None

    # --- Control ---

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def frames_processed(self) -> int:
        return self._frames_processed

    @property
    def snapshots_logged(self) -> int:
        return self._snapshots_logged

    def stop(self):
        self._running = False

    def run(self, source: FrameSource, session_id: Optional[int] = None) -> dict:
        """Consumes frames from ``source`` until exhausted or stopped."""
        if session_id is not None:
            self.session_id = session_id
        if self.session_id is None:
            raise ValueError("session_id is required to run the monitor")

        self._running = True
        self._session_start = time.monotonic()
        try:
            for frame in source:
                if not self._running:
                    break
                if frame is None:
                    continue
                self.process_frame(frame)
        finally:
            self._running = False
        return self.stats()

    def process_frame(self, frame: np.ndarray, force_log: bool = False) -> CameraSnapshot:
        """Analyzes one frame and logs it if the interval has elapsed."""
        self._frames_processed += 1
        snapshot = self.analyzer.analyze(frame)
        self._track_blinks(snapshot)

        now = time.monotonic()
        if force_log or (now - self._last_log_time) >= self.log_interval_sec:
            self._last_log_time = now
            self._log_snapshot(snapshot)
        return snapshot

    def stats(self) -> dict:
        return {
            "frames_processed": self._frames_processed,
            "snapshots_logged": self._snapshots_logged,
            "eye_samples_logged": self._eye_logged,
            "blinks_detected": self._blink_count,
        }

    # --- Internals ---

    def _track_blinks(self, snapshot: CameraSnapshot):
        if snapshot.drowsy is None:
            return
        self._last_ear.append(0.0 if snapshot.drowsy else 1.0)
        # A blink = a brief dip (drowsy=True) followed by recovery. Track a
        # simple count of dips for the session; anti-cheating will refine.
        if snapshot.drowsy and (self._last_blink_time is None or time.monotonic() - self._last_blink_time > 0.4):
            self._blink_count += 1
            self._last_blink_time = time.monotonic()
        if self.session_id is not None:
            # rough per-sample blink rate (blinks per 60s window)
            elapsed = max(1.0, time.monotonic() - getattr(self, "_session_start", time.monotonic()))
            snapshot.blink_rate = round(self._blink_count * 60.0 / elapsed, 2)

    def _log_snapshot(self, snapshot: CameraSnapshot):
        if self.session_id is None:
            return
        self.service.log_snapshot(self.session_id, snapshot)
        self._snapshots_logged += 1
        # Only log eye tracking rows when we actually have gaze data.
        if snapshot.gaze_x is not None or snapshot.gaze_y is not None:
            self.service.log_eye(self.session_id, snapshot)
            self._eye_logged += 1
        if snapshot.looking_away and self.on_warning:
            self.on_warning(self.session_id, "looking_away", "Candidate looked away from camera", "medium")
        if snapshot.drowsy and self.on_warning:
            self.on_warning(self.session_id, "drowsiness", "Candidate appears drowsy or eyes closed", "medium")
        if snapshot.face_count > 1 and self.on_warning:
            self.on_warning(self.session_id, "multiple_faces", f"Detected {snapshot.face_count} faces", "high")
        if not snapshot.face_detected and self.on_warning:
            self.on_warning(self.session_id, "no_face", "No face detected", "low")