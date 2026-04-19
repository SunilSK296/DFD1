"""
core/classifier/doc_classifier.py
Keyword-weighted document type classifier.
No ML — entirely rule-based and therefore fast, explainable, and tunable.
"""
import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.ocr.result_models import OCRResult
from core.classifier.keyword_config import (
    KEYWORD_SIGNALS,
    MIN_CLASSIFICATION_SCORE,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    doc_type: str                          # e.g. "aadhaar", "pan", "unknown"
    confidence: float                      # 0.0 – 1.0
    scores: Dict[str, float] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    reliable: bool = True                  # False if below minimum threshold


def normalize(text: str) -> str:
    """Unicode-normalise, strip, lowercase."""
    return unicodedata.normalize("NFC", text.strip().lower())


def fuzzy_match(keyword: str, text: str, threshold: int = 85) -> bool:
    """
    Use rapidfuzz partial_ratio for substring matching.
    Falls back to exact substring if rapidfuzz unavailable.
    """
    try:
        from rapidfuzz import fuzz
        return fuzz.partial_ratio(keyword.lower(), text.lower()) >= threshold
    except ImportError:
        return keyword.lower() in text.lower()


def classify_document(ocr_result: OCRResult) -> ClassificationResult:
    """
    Score each document type against OCR text and return the best match.
    """
    text_norm = normalize(ocr_result.full_text)
    raw_text = ocr_result.full_text  # keep original case for regex

    scores: Dict[str, float] = defaultdict(float)
    signals_fired: Dict[str, List[str]] = defaultdict(list)

    for doc_type, signals in KEYWORD_SIGNALS.items():
        # Primary keywords (fuzzy)
        for keyword, weight in signals.get("primary", []):
            if fuzzy_match(keyword, text_norm):
                scores[doc_type] += weight
                signals_fired[doc_type].append(f"primary:{keyword}")

        # Secondary keywords (exact substring)
        for keyword, weight in signals.get("secondary", []):
            if keyword.lower() in text_norm:
                scores[doc_type] += weight
                signals_fired[doc_type].append(f"secondary:{keyword}")

        # Regex patterns
        for pattern, weight in signals.get("pattern", []):
            if re.search(pattern, raw_text):
                scores[doc_type] += weight
                signals_fired[doc_type].append(f"pattern:{pattern}")

    if not scores or max(scores.values()) < MIN_CLASSIFICATION_SCORE:
        logger.info("Classification: insufficient signals — returning 'unknown'")
        return ClassificationResult(
            doc_type="unknown",
            confidence=0.0,
            scores=dict(scores),
            signals=[],
            reliable=False,
        )

    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values()) or 1.0
    confidence = scores[best] / total

    # Determine reliability tier
    if confidence >= 0.60:
        reliable = True
    elif confidence >= 0.35:
        reliable = True   # medium — proceed with lower weight
    else:
        reliable = False

    logger.info(
        "Classification: doc_type=%s, confidence=%.2f, top signals=%s",
        best, confidence, signals_fired[best][:3],
    )

    return ClassificationResult(
        doc_type=best,
        confidence=round(confidence, 3),
        scores=dict(scores),
        signals=signals_fired[best],
        reliable=reliable,
    )
