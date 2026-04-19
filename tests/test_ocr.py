"""
tests/test_ocr.py
Unit tests for OCR layer.
Run with: pytest tests/test_ocr.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def make_text_image(text: str, size=(400, 100), bg="white", fg="black") -> Image.Image:
    """Create a PIL image with the given text rendered on it."""
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 30), text, fill=fg, font=font)
    return img


class TestOCRResultModel:
    def test_text_block_properties(self):
        from core.ocr.result_models import TextBlock
        block = TextBlock(
            text="Hello",
            bbox=(10, 20, 110, 50),
            confidence=0.95,
        )
        assert block.width == 100
        assert block.height == 30
        assert block.center_x == 60.0
        assert block.center_y == 35.0

    def test_ocr_result_build(self):
        from core.ocr.result_models import OCRResult, TextBlock
        blocks = [
            TextBlock("Hello", (0, 0, 50, 20), 0.9),
            TextBlock("World", (60, 0, 120, 20), 0.8),
        ]
        result = OCRResult(
            blocks=blocks,
            full_text="Hello World",
            avg_confidence=0.85,
            low_confidence_count=0,
        )
        assert len(result.blocks) == 2
        assert "Hello" in result.full_text

    def test_get_low_confidence_blocks(self):
        from core.ocr.result_models import OCRResult, TextBlock
        blocks = [
            TextBlock("Good",  (0, 0, 50, 20), 0.9),
            TextBlock("Bad",   (60, 0, 120, 20), 0.3),
            TextBlock("OK",    (130, 0, 180, 20), 0.6),
        ]
        result = OCRResult(blocks=blocks, full_text="Good Bad OK", avg_confidence=0.6)
        low = result.get_low_confidence_blocks(threshold=0.5)
        assert len(low) == 1
        assert low[0].text == "Bad"

    def test_get_text_in_region(self):
        from core.ocr.result_models import OCRResult, TextBlock
        blocks = [
            TextBlock("Left",  (10, 10, 80, 40),   0.9),
            TextBlock("Right", (300, 10, 380, 40), 0.9),
        ]
        result = OCRResult(blocks=blocks, full_text="Left Right", avg_confidence=0.9)
        # Region covers only the left side (0–50% width)
        text = result.get_text_in_region((0.0, 0.0, 0.5, 1.0), (400, 60))
        assert "Left" in text
        assert "Right" not in text


class TestNormalizeText:
    def test_normalize_strips_and_lowercases(self):
        from core.ocr.engine import normalize_text
        assert normalize_text("  HELLO  ") == "hello"

    def test_normalize_unicode(self):
        from core.ocr.engine import normalize_text
        # NFC normalisation should not crash
        result = normalize_text("caf\u00e9")
        assert "caf" in result


class TestOCREngine:
    def test_run_ocr_returns_result(self):
        """OCR should return an OCRResult even on a blank image (gracefully)."""
        from core.ocr.engine import run_ocr
        img = Image.new("RGB", (200, 50), "white")
        result = run_ocr(img, use_cache=False)
        assert result is not None
        # Should have some structure
        assert hasattr(result, "blocks")
        assert hasattr(result, "full_text")

    def test_ocr_caching(self, tmp_path, monkeypatch):
        """Same image hash should hit cache on second call."""
        pytest.importorskip("diskcache", reason="diskcache not installed")
        from core.ocr import engine as ocr_engine
        import diskcache

        call_count = {"n": 0}
        original_easyocr = ocr_engine.EasyOCRReader.read

        def counting_read(image):
            call_count["n"] += 1
            return []

        monkeypatch.setattr(ocr_engine.EasyOCRReader, "read", staticmethod(counting_read))
        monkeypatch.setattr(ocr_engine.TesseractReader, "read", staticmethod(lambda img: []))

        cache_dir = tmp_path / "test_ocr_cache"
        test_cache = diskcache.Cache(str(cache_dir))
        monkeypatch.setattr(ocr_engine, "_cache", test_cache)

        img = Image.new("RGB", (100, 100), "white")
        ocr_engine.run_ocr(img, use_cache=True)
        ocr_engine.run_ocr(img, use_cache=True)

        # EasyOCR should have been called only once (second hit from cache)
        assert call_count["n"] == 1
