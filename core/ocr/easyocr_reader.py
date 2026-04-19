"""
core/ocr/easyocr_reader.py
EasyOCR wrapper with lazy singleton initialisation.
"""
import logging
from typing import List

from PIL import Image

from config.settings import OCR_LANGUAGES, OCR_GPU
from core.ocr.result_models import TextBlock

logger = logging.getLogger(__name__)


class EasyOCRReader:
    """Lazy-loaded EasyOCR singleton — load once, reuse forever."""

    _reader = None

    @classmethod
    def get_reader(cls):
        if cls._reader is None:
            try:
                import easyocr
                logger.info("Loading EasyOCR model (first run, ~10 s)…")
                cls._reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU)
                logger.info("EasyOCR model loaded.")
            except ImportError:
                logger.warning("easyocr not installed — EasyOCR unavailable.")
                cls._reader = None
        return cls._reader

    @classmethod
    def read(cls, image: Image.Image) -> List[TextBlock]:
        """
        Run EasyOCR on a PIL Image.

        Returns a list of TextBlock objects (may be empty on error).
        """
        reader = cls.get_reader()
        if reader is None:
            return []

        try:
            import numpy as np
            img_array = np.array(image.convert("RGB"))
            raw = reader.readtext(img_array, detail=1, paragraph=False)
            blocks: List[TextBlock] = []
            for idx, (bbox_pts, text, conf) in enumerate(raw):
                xs = [p[0] for p in bbox_pts]
                ys = [p[1] for p in bbox_pts]
                x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                height = y2 - y1
                blocks.append(TextBlock(
                    text=text.strip(),
                    bbox=(x1, y1, x2, y2),
                    confidence=float(conf),
                    font_size_estimate=float(height),
                    line_number=idx,
                ))
            return blocks
        except Exception as exc:
            logger.error("EasyOCR failed: %s", exc)
            return []
