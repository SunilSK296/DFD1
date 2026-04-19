"""
tests/conftest.py
Shared fixtures for pytest.
"""
import sys
from pathlib import Path

import pytest
from PIL import Image

# Ensure project root is on the Python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def blank_rgb_image():
    return Image.new("RGB", (400, 300), "white")


@pytest.fixture
def sample_text_image():
    """A simple 400×100 white image — usable as a doc stub."""
    from PIL import ImageDraw
    img = Image.new("RGB", (400, 100), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "AADHAAR  1234 5678 9012", fill="black")
    return img


@pytest.fixture
def aadhaar_ocr_result():
    from core.ocr.result_models import OCRResult, TextBlock
    text = "AADHAAR UIDAI 1234 5678 9012 DOB 01/01/1990 Government of India"
    blocks = [TextBlock(w, (i*55, 10, i*55+50, 30), 0.92) for i, w in enumerate(text.split())]
    return OCRResult(blocks=blocks, full_text=text, avg_confidence=0.92, low_confidence_count=0)


@pytest.fixture
def pan_ocr_result():
    from core.ocr.result_models import OCRResult, TextBlock
    text = "Permanent Account Number ABCDE1234F Income Tax Department Government of India"
    blocks = [TextBlock(w, (i*60, 10, i*60+55, 30), 0.90) for i, w in enumerate(text.split())]
    return OCRResult(blocks=blocks, full_text=text, avg_confidence=0.90, low_confidence_count=0)
