"""
core/explainability/report_builder.py
Assembles the final Report from all pipeline outputs.
"""
import logging
from typing import Optional
from PIL import Image

from core.ocr.result_models import OCRResult
from core.classifier.doc_classifier import ClassificationResult
from core.forgery.signal_models import ForgerySignal
from core.forgery.image_forensics import ImageForensics
from core.explainability.explainer import Explainer
from core.explainability.heatmap import (
    draw_annotated_image,
    generate_ela_image,
    build_confidence_heatmap_image,
)
from core.explainability.reason_templates import Report

logger = logging.getLogger(__name__)

_explainer = Explainer()


def build_report(
    image: Image.Image,
    ocr_result: OCRResult,
    classification: ClassificationResult,
    signals: list,
    preprocessing_meta: dict,
    image_forensics_instance: Optional[ImageForensics] = None,
) -> Report:
    """
    Full report assembly:
    1. Generate textual Report via Explainer
    2. Annotate image with signal bboxes
    3. Add ELA visualisation if available
    """
    report = _explainer.generate_report(
        signals=signals,
        doc_type=classification.doc_type,
        doc_type_confidence=classification.confidence,
        preprocessing_meta=preprocessing_meta,
        classification_signals=classification.signals,
    )

    # Annotated image
    try:
        report.annotated_image = draw_annotated_image(image, signals)
    except Exception as exc:
        logger.warning("Annotated image failed: %s", exc)
        report.annotated_image = image

    # ELA image
    try:
        if image_forensics_instance and hasattr(image_forensics_instance, "ela_map"):
            ela_map = image_forensics_instance.ela_map
            report.ela_map = ela_map
            report.ela_image = generate_ela_image(ela_map, image.size)
            report.ela_regions = getattr(image_forensics_instance, "ela_suspicious_regions", [])
        else:
            report.ela_image = None
    except Exception as exc:
        logger.warning("ELA image generation failed: %s", exc)
        report.ela_image = None

    # Heatmap overlay
    try:
        report.heatmap_image = build_confidence_heatmap_image(image, signals)
    except Exception as exc:
        logger.warning("Heatmap generation failed: %s", exc)
        report.heatmap_image = None

    return report
