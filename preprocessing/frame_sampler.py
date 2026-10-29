from app.config import settings
from app_logging.event_logger import log_event


def sample_frames(video: dict):
    """
    Samples frames from a video stream based on FPS and system limits.

    Args:
        video (dict):
            {
                "fps": float,
                "frame_count": int,
                "frames": generator(index, frame)
            }

    Returns:
        List of sampled frames (numpy arrays)
    """

    fps = video["fps"]
    frame_stream = video["frames"]

    if fps <= 0:
        raise ValueError("Invalid FPS value")

    # Calculate sampling interval
    sample_interval = max(int(fps // settings.FRAME_SAMPLE_RATE), 1)

    sampled_frames = []
    sampled_count = 0

    for frame_index, frame in frame_stream:
        if frame_index % sample_interval == 0:
            sampled_frames.append(frame)
            sampled_count += 1

        # Hard safety cap for edge devices
        if sampled_count >= settings.MAX_FRAMES:
            break

    log_event(
        "FRAMES_SAMPLED",
        {
            "sampled_frames": sampled_count,
            "sample_interval": sample_interval
        }
    )

    return sampled_frames
