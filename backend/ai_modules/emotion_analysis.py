"""
ai_modules/emotion_analysis.py
--------------------------------
Analyses facial expression / body-language stability from a video file.

CHANGE: Replaced DeepFace with MediaPipe FaceMesh.

Why:
  - DeepFace requires TensorFlow, which conflicts on Python 3.11/3.12 and
    crashes frequently due to protobuf ABI mismatches.
  - MediaPipe ships stable wheels for Python 3.8-3.12, no TF dependency,
    runs CPU-only with no extra setup.

What we measure:
  MediaPipe FaceMesh gives 468 facial landmarks per frame.  We derive three
  signals from those landmarks:

  1. Eye Aspect Ratio (EAR) -- how open the eyes are.
     Low EAR = eyes closed/squinting (nerves, distress).
     Stable, moderate EAR = calm alertness.

  2. Mouth Aspect Ratio (MAR) -- how open the mouth is.
     High MAR = mouth agape (surprise, discomfort).
     Low, stable MAR = composed speaking.

  3. Brow Distance -- vertical distance from brow to eye corner.
     High brow = raised eyebrows (surprise, anxiety).
     Stable brow = neutral or positive engagement.

  We compute the std-dev of each signal across all sampled frames and
  convert to a single stability_score in [0, 1] where:
    1.0 = calm, engaged, confident
    0.0 = highly erratic/nervous face movements

Returns:
    dict with key "stability_score" (float 0-1).
    Falls back to {"stability_score": 0.5} if no face detected.
"""

import cv2
import numpy as np
from pathlib import Path

try:
    import mediapipe as mp
    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False

# MediaPipe landmark indices (468-point FaceMesh)
_LEFT_EYE  = [33, 160, 158, 133, 153, 144]
_RIGHT_EYE = [362, 385, 387, 263, 373, 380]
_MOUTH     = [61, 291, 13, 14]
_L_BROW    = 105
_L_EYE_TOP = 159
_R_BROW    = 334
_R_EYE_TOP = 386


def _ear(landmarks, indices):
    pts = [landmarks[i] for i in indices]
    h = ((pts[0].x - pts[3].x)**2 + (pts[0].y - pts[3].y)**2) ** 0.5
    v1 = ((pts[1].x - pts[5].x)**2 + (pts[1].y - pts[5].y)**2) ** 0.5
    v2 = ((pts[2].x - pts[4].x)**2 + (pts[2].y - pts[4].y)**2) ** 0.5
    return (v1 + v2) / (2.0 * h) if h > 1e-6 else 0.0


def _mar(landmarks):
    l = (landmarks[_MOUTH[0]].x, landmarks[_MOUTH[0]].y)
    r = (landmarks[_MOUTH[1]].x, landmarks[_MOUTH[1]].y)
    t = (landmarks[_MOUTH[2]].x, landmarks[_MOUTH[2]].y)
    b = (landmarks[_MOUTH[3]].x, landmarks[_MOUTH[3]].y)
    h = ((l[0]-r[0])**2 + (l[1]-r[1])**2) ** 0.5
    v = ((t[0]-b[0])**2 + (t[1]-b[1])**2) ** 0.5
    return v / h if h > 1e-6 else 0.0


def _brow_raise(landmarks):
    lb = (landmarks[_L_BROW].x,    landmarks[_L_BROW].y)
    le = (landmarks[_L_EYE_TOP].x, landmarks[_L_EYE_TOP].y)
    rb = (landmarks[_R_BROW].x,    landmarks[_R_BROW].y)
    re = (landmarks[_R_EYE_TOP].x, landmarks[_R_EYE_TOP].y)
    dl = ((lb[0]-le[0])**2 + (lb[1]-le[1])**2) ** 0.5
    dr = ((rb[0]-re[0])**2 + (rb[1]-re[1])**2) ** 0.5
    return (dl + dr) / 2.0


def analyze_emotions(video_path: str, frame_interval: int = 15) -> dict:
    """
    Analyse facial stability in a video using MediaPipe FaceMesh.

    Args:
        video_path:     Path to the video file (.webm, .mp4, .avi, etc.)
        frame_interval: Sample every Nth frame.

    Returns:
        {"stability_score": float}  -- 0.0 (erratic) to 1.0 (stable/calm)
    """
    neutral = {"stability_score": 0.5}

    if not Path(video_path).exists():
        return neutral

    if not _MP_AVAILABLE:
        return neutral

    mp_face = mp.solutions.face_mesh
    cap = cv2.VideoCapture(str(video_path))
    ears, mars, brows = [], [], []
    frame_idx = 0

    with mp_face.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.4,
        min_tracking_confidence=0.4,
    ) as face_mesh:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = face_mesh.process(rgb)
                if res.multi_face_landmarks:
                    lm = res.multi_face_landmarks[0].landmark
                    try:
                        ears.append((_ear(lm, _LEFT_EYE) + _ear(lm, _RIGHT_EYE)) / 2)
                        mars.append(_mar(lm))
                        brows.append(_brow_raise(lm))
                    except Exception:
                        pass
            frame_idx += 1

    cap.release()

    if len(ears) < 3:
        return neutral

    def cv_stability(arr):
        a = np.array(arr)
        mean = a.mean()
        if mean < 1e-6:
            return 0.5
        cv = a.std() / mean
        return float(np.clip(1.0 - cv / 0.5, 0.0, 1.0))

    stability = (
        cv_stability(ears)  * 0.45 +
        cv_stability(brows) * 0.35 +
        cv_stability(mars)  * 0.20
    )
    return {"stability_score": round(stability, 3)}


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_video.webm"
    print(analyze_emotions(path))
