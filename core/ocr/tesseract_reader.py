"""
core/ocr/tesseract_reader.py
Tesseract fallback OCR reader.
"""
import logging
from typing import List

from PIL import Image

from core.ocr.result_models import TextBlock

logger = logging.getLogger(__name__)

TESSERACT_LANG = "eng"  # extend to 'eng+hin+kan+tel' if lang packs installed


class TesseractReader:
    """Thin wrapper around pytesseract for fallback OCR."""

    @staticmethod
    def read(image: Image.Image) -> List[TextBlock]:
        try:
            import pytesseract
            data = pytesseract.image_to_data(
                image.convert("RGB"),
                lang=TESSERACT_LANG,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            logger.error("Tesseract failed: %s", exc)
            return []

        blocks: List[TextBlock] = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            if not text:
                continue
            conf = int(data["conf"][i])
            if conf < 0:
                continue
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]
            blocks.append(TextBlock(
                text=text,
                bbox=(x, y, x + w, y + h),
                confidence=conf / 100.0,
                font_size_estimate=float(h),
                line_number=data["line_num"][i],
            ))
        return blocks
