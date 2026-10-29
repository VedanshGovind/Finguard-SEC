"""
inference/live_pipeline.py

Fast path for /analyze/live-verification. The MODEL IS NOT CHANGED: the same
Xception weights are called through the same run_inference(); this module only
decides which frames reach it, and extracts audio once instead of up to three times.
"""

import os
import shutil
import subprocess
import tempfile
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np
from fastapi import HTTPException

from app.config import settings
from app_logging.event_logger import log_event
from face_detection.face_detector import detect_primary_faces
from inference.deepfake_infer import run_inference
from inference.temporal_aggregation import aggregate_predictions
from preprocessing.normalization import normalize_frames


# ---------------------------------------------------------------------------
# Frame reading
# ---------------------------------------------------------------------------
def _read_candidates(video_path: str) -> Tuple[List[Tuple[int, np.ndarray]], float]:
    """
    Read the clip once and keep ~LIVE_CANDIDATE_FPS frames per second as
    (frame_index, BGR frame). Frames that are not kept are only grab()-ed
    (no colour conversion / copy), and the capture is always released, so the
    temp file can be deleted afterwards (matters on Windows).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(status_code=422, detail="Could not read the recorded video")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        # Browser .webm often reports fps = 0 / 1000
        if not fps or fps <= 0 or fps > 240:
            fps = 30.0
        step = max(int(round(fps / settings.LIVE_CANDIDATE_FPS)), 1)

        out, idx = [], 0
        while len(out) < settings.LIVE_CANDIDATE_CAP:
            if not cap.grab():
                break
            if idx % step == 0:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    h, w = frame.shape[:2]
                    if w > 960:  # bound memory for 1080p webcams
                        frame = cv2.resize(frame, (960, int(h * 960 / w)), interpolation=cv2.INTER_AREA)
                    out.append((idx, frame))
            idx += 1
        return out, fps
    finally:
        cap.release()


def _spread(items: list, n: int) -> list:
    """n items evenly spread across the list (keeps the whole clip represented)."""
    if len(items) <= n:
        return list(items)
    pos = np.linspace(0, len(items) - 1, n).round().astype(int)
    return [items[i] for i in pos]


# ---------------------------------------------------------------------------
# Video score
# ---------------------------------------------------------------------------
def live_video_score(video_path: str) -> Tuple[float, dict]:
    """
    Returns (video_score, meta). Raises HTTPException(422) when no face is found.
    """
    t0 = time.perf_counter()
    candidates, fps = _read_candidates(video_path)
    t_read = time.perf_counter()

    if not candidates:
        raise HTTPException(status_code=422, detail="No video frames found in the recording")

    # Ignore the first moments (auto-exposure / focus hunting) when there is enough footage.
    skip_before = int(settings.LIVE_SKIP_FIRST_SECONDS * fps)
    usable = [c for c in candidates if c[0] >= skip_before]
    if len(usable) < settings.LIVE_MAX_FRAMES // 2:
        usable = candidates

    n = settings.LIVE_MAX_FRAMES
    first_pass = _spread(usable, n)
    faces = detect_primary_faces(normalize_frames([f for _, f in first_pass]))

    # Not enough faces (dim room, head turned)? look at the remaining frames too.
    if len(faces) < max(4, n // 3):
        used = {i for i, _ in first_pass}
        rest = [c for c in candidates if c[0] not in used]
        faces += detect_primary_faces(normalize_frames([f for _, f in _spread(rest, n)]))

    t_detect = time.perf_counter()

    if len(faces) == 0:
        raise HTTPException(
            status_code=422,
            detail="No face detected. Face the camera in good lighting and try again.",
        )

    score = float(aggregate_predictions(run_inference(faces)))
    t_infer = time.perf_counter()

    meta = {
        "frames_read": len(candidates),
        "faces_scored": len(faces),
        "ms": {
            "read": round((t_read - t0) * 1000),
            "detect": round((t_detect - t_read) * 1000),
            "infer": round((t_infer - t_detect) * 1000),
        },
    }
    log_event("LIVE_VIDEO_SCORED", {"score": score, **meta})
    return score, meta


# ---------------------------------------------------------------------------
# Audio extraction (once, shared by the audio model and the code verifier)
# ---------------------------------------------------------------------------
def _ffmpeg_exe() -> Optional[str]:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:  # ffmpeg binary bundled with moviepy
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def extract_wav(media_path: str, max_seconds: int = 15) -> Optional[str]:
    """
    Extract a 16 kHz mono WAV from the recording. Returns the wav path (caller deletes
    it) or None if extraction failed, in which case callers fall back to the original
    file and their own legacy extraction code.
    """
    exe = _ffmpeg_exe()
    if not exe:
        return None
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        r = subprocess.run(
            [exe, "-y", "-loglevel", "error", "-i", media_path, "-vn",
             "-ac", "1", "-ar", "16000", "-t", str(max_seconds), wav],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
        )
        if r.returncode == 0 and os.path.getsize(wav) > 1000:
            return wav
    except Exception:
        pass
    try:
        os.remove(wav)
    except OSError:
        pass
    return None