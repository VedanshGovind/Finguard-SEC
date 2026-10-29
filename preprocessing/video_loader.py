import cv2
import os

from app.config import settings
from app_logging.event_logger import log_event


def load_video(video_path: str):
    """
    Loads a video file safely for edge inference.

    Returns:
        dict containing:
            - fps
            - frame_count
            - frames (lazy generator)
    """

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError("Failed to open video stream")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Browser-recorded .webm files often report fps = 0 or 1000 and no frame count.
    # Fall back to a sane default so frame sampling still works.
    if not fps or fps <= 0 or fps > 240:
        fps = 30.0
    if total_frames < 0:
        total_frames = 0

    log_event(
        "VIDEO_LOADED",
        {
            "fps": fps,
            "total_frames": total_frames,
            "path": video_path
        }
    )

    def frame_generator():
        frame_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            yield frame_index, frame
            frame_index += 1

        cap.release()

    return {
        "fps": fps,
        "frame_count": total_frames,
        "frames": frame_generator()
    }