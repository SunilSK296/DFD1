"""
core/__init__.py
Top-level pipeline runner.
"""
import logging
from typing import Optional

from PIL import Image

from core.ingestion import load_document
from core.preprocessor import preprocess
from core.ocr.engine import run_ocr
from core.classifier.doc_classifier import classify_document
from core.forgery.orchestrator import ForgeryOrchestrator
from core.forgery.image_forensics import ImageForensics
from core.explainability.report_builder import build_report
from core.explainability.reason_templates import Report

logger = logging.getLogger(__name__)

_orchestrator = ForgeryOrchestrator()


def analyze_document(file_source, use_ocr_cache: bool = True) -> Report:
    """
    Full end-to-end pipeline.

    Args:
        file_source: file path str, Path, bytes, or Streamlit UploadedFile
        use_ocr_cache: whether to use disk-cached OCR results

    Returns:
        Report dataclass with verdict, score, reasons, annotated images
    """
    logger.info("=== Starting document analysis ===")

    # 1. Ingest
    image, ingest_meta = load_document(file_source)
    logger.info("Ingestion complete: %s", ingest_meta)

    # 2. Preprocess
    image, preprocess_meta = preprocess(image)
    preprocess_meta.update(ingest_meta)

    # 3. OCR
    ocr_result = run_ocr(image, use_cache=use_ocr_cache)

    # 4. Classify
    classification = classify_document(ocr_result)
    logger.info("Classification: %s (conf=%.2f)", classification.doc_type, classification.confidence)

    # 5. Forgery detection
    signals = _orchestrator.analyze(image, ocr_result, classification.doc_type)

    # 6. Build report
    report = build_report(
        image=image,
        ocr_result=ocr_result,
        classification=classification,
        signals=signals,
        preprocessing_meta=preprocess_meta,
        image_forensics_instance=_orchestrator.image_forensics,
    )

    logger.info(
        "=== Analysis done: verdict=%s, score=%.1f ===",
        report.verdict, report.confidence_score,
    )
    return report
