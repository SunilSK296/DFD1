"""
core/ocr/engine.py
OCR orchestrator — tries EasyOCR first, falls back to Tesseract.
Results are cached on disk keyed by image MD5 to make re-analysis instant.
"""
import hashlib
import logging
import unicodedata
from typing import List

from PIL import Image

from config.settings import OCR_CACHE_DIR, OCR_CACHE_TTL
from core.ocr.result_models import OCRResult, TextBlock
from core.ocr.easyocr_reader import EasyOCRReader
from core.ocr.tesseract_reader import TesseractReader

logger = logging.getLogger(__name__)

try:
    import diskcache
    _cache = diskcache.Cache(str(OCR_CACHE_DIR))
except ImportError:
    logger.warning("diskcache not available — OCR caching disabled.")
    _cache = None


def _image_hash(image: Image.Image) -> str:
    return hashlib.md5(image.tobytes()).hexdigest()


def _merge_blocks(primary: List[TextBlock], fallback: List[TextBlock]) -> List[TextBlock]:
    """
    Use primary (EasyOCR) results if they exist; supplement with Tesseract
    blocks that don't overlap significantly with existing bboxes.
    """
    if not primary:
        return fallback
    return primary  # simple strategy: trust EasyOCR when available


def _build_result(blocks: List[TextBlock]) -> OCRResult:
    """Aggregate raw TextBlock list into an OCRResult."""
    if not blocks:
        return OCRResult()

    full_text = " ".join(b.text for b in blocks if b.text)
    confidences = [b.confidence for b in blocks]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    low_conf = sum(1 for c in confidences if c < 0.5)

    langs = list({b.language for b in blocks if b.language})

    return OCRResult(
        blocks=blocks,
        full_text=full_text,
        languages_detected=langs or ["en"],
        avg_confidence=round(avg_conf, 3),
        low_confidence_count=low_conf,
    )


def normalize_text(text: str) -> str:
    """Unicode-normalise + strip for consistent matching."""
    return unicodedata.normalize("NFC", text.strip().lower())


def run_ocr(image: Image.Image, use_cache: bool = True) -> OCRResult:
    """
    Main entry point for OCR.

    1. Check disk cache by image hash.
    2. Run EasyOCR; fall back to Tesseract if empty.
    3. Cache result and return OCRResult.
    """
    image_hash = _image_hash(image)

    if use_cache and _cache is not None:
        cached = _cache.get(image_hash)
        if cached is not None:
            logger.debug("OCR cache hit for %s", image_hash[:8])
            return cached

    logger.info("Running OCR (hash=%s)…", image_hash[:8])

    primary_blocks = EasyOCRReader.read(image)
    if not primary_blocks:
        logger.info("EasyOCR returned no results — trying Tesseract fallback.")
        fallback_blocks = TesseractReader.read(image)
        blocks = fallback_blocks
    else:
        fallback_blocks = []
        blocks = _merge_blocks(primary_blocks, fallback_blocks)

    result = _build_result(blocks)
    logger.info(
        "OCR done: %d blocks, avg_conf=%.2f, languages=%s",
        len(blocks), result.avg_confidence, result.languages_detected,
    )

    if use_cache and _cache is not None:
        _cache.set(image_hash, result, expire=OCR_CACHE_TTL)

    return result
