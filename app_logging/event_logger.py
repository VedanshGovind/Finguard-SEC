"""
logging/event_logger.py

Responsibilities:
- Standardized event logging across the pipeline.
- Console output for real-time monitoring.
- JSON-based file logging for post-analysis in offline environments.
"""

import logging
import json
import os
from datetime import datetime
from app.config import settings

# Setup standard python logging
logger = logging.getLogger("DeepfakeEdgeAgent")
logger.setLevel(settings.LOG_LEVEL)

# Create log directory if it doesn't exist
os.makedirs(settings.LOG_DIR, exist_ok=True)
log_file_path = os.path.join(settings.LOG_DIR, "system_events.jsonl")

def log_event(event_type: str, data: dict):
    """
    Logs a system event with a timestamp and structured metadata.
    
    Args:
        event_type (str): The name of the event (e.g., 'FACES_DETECTED')
        data (dict): Contextual information related to the event
    """
    if not settings.ENABLE_EVENT_LOGGING:
        return

    event_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "metadata": data,
        "env": settings.ENV,
        "runtime_mode": settings.RUNTIME_MODE
    }

    # 1. Print to Console (for Docker/Uvicorn logs)
    # Using a simple string format for readability in console
    logger.info(f"[{event_type}] - {json.dumps(data)}")

    # 2. Persist to Disk (JSON Lines format for easy parsing)
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_entry) + "\n")
    except Exception as e:
        # Fallback to console if file writing fails
        print(f"CRITICAL: Failed to write to log file: {e}")

# Initialize basic config for the logger
if not logger.handlers:
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)