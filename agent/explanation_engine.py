"""
agent/explanation_engine.py

Responsibilities:
- Convert ML confidence and policy flags into human-readable text.
- Provide transparency on why a specific verdict was reached.
- Support multi-level risk explanations based on system state.
"""

from typing import Dict, Any


def generate_explanation(verdict: str, confidence: float, risk_level: str) -> str:
    """
    Generates a natural language explanation for the pipeline's decision.

    Args:
        verdict: The final decision ('DEEPFAKE', 'REAL', 'UNCERTAIN')
        confidence: The numerical aggregated score from the model
        risk_level: The policy-adjusted risk category

    Returns:
        str: A concise explanation for the user.
    """
    
    # Ensure confidence is a float
    safe_confidence = float(confidence)
    
    # Format confidence as a percentage for readability
    percentage = round(safe_confidence * 100, 2)
    
    # Base explanations mapping
    if verdict == "DEEPFAKE":
        base_msg = f"The system detected strong indicators of digital manipulation (Confidence: {percentage}%)."
    elif verdict == "REAL":
        base_msg = f"The analysis suggests the media is authentic (Confidence: {100 - percentage}% real)."
    else:
        base_msg = "The analysis resulted in an ambiguous verdict."

    # Add risk-specific context
    if risk_level == "CRITICAL":
        risk_msg = " This media shows high-probability synthesis and should be treated as high-risk content."
    elif risk_level == "HIGH":
        risk_msg = " Significant anomalies were found. Manual verification is strongly recommended."
    elif risk_level == "MEDIUM":
        risk_msg = " The system encountered conflicting patterns. Please review the detailed analysis."
    else:
        risk_msg = " No significant anomalies detected."

    return f"{base_msg}{risk_msg}"


# Overloaded version for backward compatibility
def generate_explanation_from_decision(score: float, decision: Dict[str, Any]) -> str:
    """
    Helper function to match alternative call signatures.
    """
    return generate_explanation(
        verdict=decision.get("verdict", "UNCERTAIN"),
        confidence=score,
        risk_level=decision.get("risk_level", "LOW")
    )