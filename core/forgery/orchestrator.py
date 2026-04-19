"""
core/forgery/orchestrator.py
Runs all 4 forgery subsystems in parallel where possible.
One subsystem crashing never takes down the whole pipeline.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from PIL import Image

from core.ocr.result_models import OCRResult
from core.forgery.signal_models import ForgerySignal
from core.forgery.text_validator import TextValidator
from core.forgery.layout_validator import LayoutValidator
from core.forgery.font_analyzer import FontAnalyzer
from core.forgery.image_forensics import ImageForensics

logger = logging.getLogger(__name__)


class ForgeryOrchestrator:
    """Coordinates all forgery detection subsystems."""

    def __init__(self):
        self.text_validator = TextValidator()
        self.layout_validator = LayoutValidator()
        self.font_analyzer = FontAnalyzer()
        self.image_forensics = ImageForensics()

    def analyze(
        self,
        image: Image.Image,
        ocr_result: OCRResult,
        doc_type: str,
    ) -> List[ForgerySignal]:
        """
        Run all subsystems. Returns aggregated list of ForgerySignals.
        Text, Layout, Font run in threads; ImageForensics in main thread (OpenCV GIL).
        """
        all_signals: List[ForgerySignal] = []

        def safe_run(name, fn, *args):
            try:
                result = fn(*args)
                logger.debug("Subsystem '%s': %d signals", name, len(result))
                return result
            except Exception as exc:
                logger.warning("Subsystem '%s' failed: %s", name, exc, exc_info=True)
                return []

        # Threaded subsystems
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    safe_run, "text", self.text_validator.validate, ocr_result, doc_type
                ): "text",
                executor.submit(
                    safe_run, "layout", self.layout_validator.validate, image, ocr_result, doc_type
                ): "layout",
                executor.submit(
                    safe_run, "font", self.font_analyzer.analyze, image, ocr_result
                ): "font",
            }
            for future in as_completed(futures):
                all_signals.extend(future.result())

        # Image forensics in main thread
        image_signals = safe_run(
            "image", self.image_forensics.analyze, image
        )
        all_signals.extend(image_signals)

        logger.info(
            "Forgery analysis complete: %d total signals across all subsystems",
            len(all_signals),
        )
        return all_signals
