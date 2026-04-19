"""
core/scoring/scorer.py
Weighted signal aggregation → normalised risk score [0–100].
Sigmoid normalisation prevents a single catastrophic signal from maxing the score.
"""
import logging
import math
import os
from pathlib import Path
from typing import List, Dict, Tuple

import yaml

from core.forgery.signal_models import ForgerySignal

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "score_config.yaml"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as fh:
            return yaml.safe_load(fh)
    except Exception as exc:
        logger.error("Failed to load score config: %s", exc)
        return {
            "weights": {},
            "default_weight": 10,
            "thresholds": {"genuine": 25, "review": 55},
            "normalization": {"method": "sigmoid", "scale_factor": 80},
        }


_CONFIG = _load_config()
_WEIGHTS: Dict[str, float] = _CONFIG.get("weights", {})
_DEFAULT_WEIGHT: float = float(_CONFIG.get("default_weight", 10))
_THRESHOLDS = _CONFIG.get("thresholds", {"genuine": 25, "review": 55})
_SIGMOID_SCALE = float(_CONFIG.get("normalization", {}).get("scale_factor", 80))


def compute_score(signals: List[ForgerySignal]) -> float:
    """
    Aggregate signal weights → normalised [0–100] risk score.

    Formula:
        raw  = Σ weight(signal) × confidence(signal)
        score = 100 × (1 − exp(−raw / scale_factor))
    """
    raw_score = sum(
        _WEIGHTS.get(s.signal_type, _DEFAULT_WEIGHT) * s.confidence
        for s in signals
    )
    normalised = 100.0 * (1.0 - math.exp(-raw_score / _SIGMOID_SCALE))
    return round(min(normalised, 100.0), 1)


def score_to_verdict(score: float) -> Tuple[str, str]:
    """
    Returns (verdict_label, css_color) based on score thresholds.

    Verdicts:
        GENUINE       score ≤ genuine_threshold
        NEEDS REVIEW  genuine_threshold < score ≤ review_threshold
        SUSPICIOUS    score > review_threshold
    """
    genuine_max = _THRESHOLDS.get("genuine", 25)
    review_max = _THRESHOLDS.get("review", 55)

    if score <= genuine_max:
        return "GENUINE", "#2ecc71"        # green
    elif score <= review_max:
        return "NEEDS REVIEW", "#f39c12"   # amber
    else:
        return "SUSPICIOUS", "#e74c3c"     # red


def get_subsystem_breakdown(signals: List[ForgerySignal]) -> Dict[str, float]:
    """
    Returns per-subsystem raw score contribution (un-normalised, for display).
    """
    breakdown: Dict[str, float] = {}
    for s in signals:
        contribution = _WEIGHTS.get(s.signal_type, _DEFAULT_WEIGHT) * s.confidence
        breakdown[s.subsystem] = breakdown.get(s.subsystem, 0.0) + contribution
    return breakdown
