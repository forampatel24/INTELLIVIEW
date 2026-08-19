"""Pure geometry helpers over MediaPipe FaceMesh landmarks.

Landmarks expose normalized ``.x`` / ``.y`` / ``.z`` attributes in [0, 1].
These functions only need the landmark objects (indexable by FaceMesh index)
so they can be unit-tested with lightweight stubs.

FaceMesh 468-landmark indices used:
    LEFT_EYE_OUTER=33   LEFT_EYE_INNER=133   LEFT_EYE_TOP=159     LEFT_EYE_BOTTOM=145
    RIGHT_EYE_OUTER=362 RIGHT_EYE_INNER=263  RIGHT_EYE_TOP=386    RIGHT_EYE_BOTTOM=374
    NOSE_TIP=1  MOUTH_LEFT=61  MOUTH_RIGHT=291  MOUTH_TOP=13  MOUTH_BOTTOM=14
"""

from typing import Optional

LEFT_EYE_INDICES = (33, 159, 145, 133, 386, 374)
RIGHT_EYE_INDICES = (362, 386, 374, 263, 159, 145)
# FaceMesh order for each eye: (outer, top, bottom, inner, left_top, right_top) —
# we use the canonical 6-point EAR layout instead (p1..p6 around the eye).
EAR_LEFT = (33, 159, 158, 133, 153, 144)
EAR_RIGHT = (362, 385, 387, 263, 373, 380)

MOUTH_INDICES = (61, 291, 13, 14)

NOSE_TIP = 1
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 362
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 263

# Typical EAR thresholds for a face looking at the camera.
BLINK_EAR_THRESHOLD = 0.21
GAZE_LOOKING_AWAY_X = 0.45
GAZE_LOOKING_AWAY_Y = 0.35
GAZE_CONTACT_RANGE = 0.25


def _distance(a, b) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def eye_aspect_ratio(landmarks, eye_indices=EAR_RIGHT) -> Optional[float]:
    """EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|). None if points missing."""
    if len(landmarks) <= max(eye_indices):
        return None
    p1, p2, p3, p4, p5, p6 = (landmarks[i] for i in eye_indices)
    denom = 2.0 * _distance(p1, p4)
    if denom <= 1e-9:
        return None
    return (_distance(p2, p6) + _distance(p3, p5)) / denom


def mouth_aspect_ratio(landmarks) -> Optional[float]:
    """MAR = |top-bottom| / |left-right|. None if points missing."""
    if len(landmarks) <= max(MOUTH_INDICES):
        return None
    left, right, top, bottom = (landmarks[i] for i in MOUTH_INDICES)
    width = _distance(left, right)
    if width <= 1e-9:
        return None
    return _distance(top, bottom) / width


def _face_center_x(landmarks) -> Optional[float]:
    if len(landmarks) <= max(LEFT_EYE_INNER, RIGHT_EYE_INNER):
        return None
    return (landmarks[LEFT_EYE_INNER].x + landmarks[RIGHT_EYE_INNER].x) / 2.0


def _inter_eye_width(landmarks) -> Optional[float]:
    if len(landmarks) <= max(LEFT_EYE_OUTER, RIGHT_EYE_OUTER):
        return None
    return abs(landmarks[RIGHT_EYE_OUTER].x - landmarks[LEFT_EYE_OUTER].x)


def gaze_offset_x(landmarks) -> Optional[float]:
    """Horizontal nose deviation from the face center, normalized to [-1, 1].

    Uses half the inter-eye distance as the scale so a shift of roughly half
    the face width reads as 1.0. Positive = nose to the right of center.
    """
    cx = _face_center_x(landmarks)
    width = _inter_eye_width(landmarks)
    if cx is None or width is None or width <= 1e-9:
        return None
    return max(-1.0, min(1.0, (cx - landmarks[NOSE_TIP].x) / (0.5 * width)))


def gaze_offset_y(landmarks) -> Optional[float]:
    """Vertical nose deviation from its expected position, normalized to [-1, 1].

    The expected nose position is the midpoint of the eye line and the mouth
    line; a centered face sits naturally there, so the offset is ~0. Positive
    = nose lower than expected (chin down / looking down).
    """
    if len(landmarks) <= max(MOUTH_INDICES):
        return None
    eye_line_y = (landmarks[LEFT_EYE_INNER].y + landmarks[RIGHT_EYE_INNER].y) / 2.0
    mouth_y = (landmarks[MOUTH_INDICES[0]].y + landmarks[MOUTH_INDICES[1]].y +
               landmarks[MOUTH_INDICES[2]].y + landmarks[MOUTH_INDICES[3]].y) / 4.0
    width = _inter_eye_width(landmarks)
    if width is None or width <= 1e-9:
        return None
    expected_nose_y = (eye_line_y + mouth_y) / 2.0
    return max(-1.0, min(1.0, (landmarks[NOSE_TIP].y - expected_nose_y) / (0.5 * width)))


def eye_contact(landmarks, range_x: float = GAZE_CONTACT_RANGE) -> Optional[bool]:
    ox, oy = gaze_offset_x(landmarks), gaze_offset_y(landmarks)
    if ox is None or oy is None:
        return None
    return abs(ox) <= range_x and abs(oy) <= range_x


def looking_away(landmarks) -> Optional[bool]:
    ox, oy = gaze_offset_x(landmarks), gaze_offset_y(landmarks)
    if ox is None or oy is None:
        return None
    return abs(ox) > GAZE_LOOKING_AWAY_X or abs(oy) > GAZE_LOOKING_AWAY_Y


def head_movement(landmarks) -> Optional[float]:
    """Relative head position (0..1) vs the face center, from outer eye corners."""
    if len(landmarks) <= max(LEFT_EYE_OUTER, RIGHT_EYE_OUTER, NOSE_TIP):
        return None
    center_x = (landmarks[LEFT_EYE_OUTER].x + landmarks[RIGHT_EYE_OUTER].x) / 2.0
    face_width = abs(landmarks[RIGHT_EYE_OUTER].x - landmarks[LEFT_EYE_OUTER].x)
    if face_width <= 1e-9:
        return None
    return max(0.0, min(1.0, abs(landmarks[NOSE_TIP].x - center_x) / face_width))


def is_drowsy(landmarks, ear_threshold: float = BLINK_EAR_THRESHOLD) -> Optional[bool]:
    """True when the average EAR of both eyes is below the blink threshold."""
    left = eye_aspect_ratio(landmarks, EAR_LEFT)
    right = eye_aspect_ratio(landmarks, EAR_RIGHT)
    if left is None or right is None:
        return None
    return (left + right) / 2.0 < ear_threshold
