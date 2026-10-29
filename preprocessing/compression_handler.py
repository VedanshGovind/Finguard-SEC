"""
preprocessing/compression_handler.py

Responsibilities:
- Optimize video size for edge-device constraints.
- Standardize bitrate to maintain consistent quality for ML inference.
- Ensure efficient frame extraction by using standard codecs.
"""

import subprocess
import os
from app.config import settings
from app_logging.event_logger import log_event

def handle_compression(input_path: str) -> str:
    """
    Standardizes video compression to ensure optimal processing speed 
    and model performance.
    
    Returns:
        str: Path to the optimized/compressed video.
    """
    output_path = input_path.replace(".", "_optimized.")
    
    # Check if compression is needed based on file size
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    
    # If the file is already small, skip re-encoding to save time
    if file_size_mb < 10.0:
        log_event("COMPRESSION_SKIPPED", {"reason": "Small file size", "size_mb": file_size_mb})
        return input_path

    log_event("COMPRESSION_STARTED", {"input_size_mb": file_size_mb})

    # FFmpeg command for standardizing video:
    # - Crf 23 is a good balance between quality and size
    # - Preset 'ultrafast' ensures speed on edge CPUs
    # - Scaling can be added if needed, but here we prioritize bitrate
    command = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", "23",
        "-preset", "ultrafast",
        "-acodec", "copy",  # Don't waste time re-encoding audio
        output_path
    ]

    try:
        # Run compression (requires FFmpeg installed on the system)
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        new_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        log_event("COMPRESSION_COMPLETE", {
            "original_size_mb": round(file_size_mb, 2),
            "new_size_mb": round(new_size_mb, 2)
        })
        return output_path

    except subprocess.CalledProcessError as e:
        log_event("COMPRESSION_FAILED", {"error": str(e)})
        # If compression fails, we fallback to the original to keep the pipeline moving
        return input_path