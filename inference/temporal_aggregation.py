import numpy as np
from typing import List

from app_logging.event_logger import log_event


def aggregate_predictions(predictions: List[float]) -> float:
    """
    Aggregates per-face / per-frame predictions into a single video-level score.

    Strategy:
    - Remove extreme outliers
    - Use robust central tendency (median)
    - Smooth decision noise across time

    Args:
        predictions: List of deepfake probabilities [0,1]

    Returns:
        float: aggregated deepfake confidence score
    """

    if not predictions:
        return 0.0

    scores = np.array(predictions, dtype=np.float32)

    # Clip for numerical safety
    scores = np.clip(scores, 0.0, 1.0)

    # Remove extreme outliers (top & bottom 5%)
    lower = np.percentile(scores, 5)
    upper = np.percentile(scores, 95)
    filtered_scores = scores[(scores >= lower) & (scores <= upper)]

    if len(filtered_scores) == 0:
        filtered_scores = scores

    # Robust aggregation
    final_score = float(np.median(filtered_scores))

    log_event(
        "TEMPORAL_AGGREGATION_COMPLETE",
        {
            "raw_count": len(scores),
            "filtered_count": len(filtered_scores),
            "final_score": final_score
        }
    )

    return final_score
