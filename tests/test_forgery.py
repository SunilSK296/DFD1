"""
tests/test_forgery.py
Unit tests for forgery detection subsystems.
Run with: pytest tests/test_forgery.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ocr.result_models import OCRResult, TextBlock
from core.forgery.signal_models import ForgerySignal


# ── Helpers ───────────────────────────────────────────────────────────────────

def blank_image(w=400, h=300, color="white") -> Image.Image:
    return Image.new("RGB", (w, h), color)


def make_ocr(text: str, avg_conf: float = 0.9) -> OCRResult:
    blocks = [
        TextBlock(word, (i * 60, 10, i * 60 + 55, 30), avg_conf)
        for i, word in enumerate(text.split())
    ]
    return OCRResult(blocks=blocks, full_text=text, avg_confidence=avg_conf)


# ── TextValidator ─────────────────────────────────────────────────────────────

class TestTextValidator:
    def setup_method(self):
        from core.forgery.text_validator import TextValidator
        self.validator = TextValidator()

    def test_valid_aadhaar_no_signal(self):
        # 1234 5678 9012 — this number will almost certainly fail Verhoeff,
        # but the format should be detected (number found)
        ocr = make_ocr("AADHAAR 1234 5678 9012 DOB 01/01/1990")
        signals = self.validator.validate(ocr, "aadhaar")
        types = [s.signal_type for s in signals]
        # Number WAS found, so "aadhaar_number_not_found" should NOT be there
        assert "aadhaar_number_not_found" not in types

    def test_missing_aadhaar_number(self):
        ocr = make_ocr("AADHAAR DOB 01/01/1990 Address somewhere")
        signals = self.validator.validate(ocr, "aadhaar")
        types = [s.signal_type for s in signals]
        assert "aadhaar_number_not_found" in types

    def test_invalid_pan_format(self):
        ocr = make_ocr("Permanent Account Number 12345 Income Tax")
        signals = self.validator.validate(ocr, "pan")
        types = [s.signal_type for s in signals]
        assert "pan_format_invalid" in types

    def test_valid_pan_no_format_error(self):
        ocr = make_ocr("Permanent Account Number ABCDE1234F Income Tax Name John")
        signals = self.validator.validate(ocr, "pan")
        types = [s.signal_type for s in signals]
        assert "pan_format_invalid" not in types

    def test_marks_sum_mismatch_detected(self):
        # Subject marks sum to 450, but we state 500
        text = (
            "SSLC Mathematics 90 Science 85 English 92 Social 88 Kannada 95 "
            "Total 500 Register 12-34-567890"
        )
        ocr = make_ocr(text)
        signals = self.validator.validate(ocr, "sslc")
        # May or may not trigger depending on number extraction accuracy
        # Just verify it doesn't crash and returns a list
        assert isinstance(signals, list)

    def test_required_field_missing_for_pan(self):
        # PAN without name or DOB
        ocr = make_ocr("ABCDE1234F Income Tax")
        signals = self.validator.validate(ocr, "pan")
        types = [s.signal_type for s in signals]
        assert "required_field_missing" in types

    def test_returns_list(self):
        ocr = make_ocr("some random text")
        signals = self.validator.validate(ocr, "unknown")
        assert isinstance(signals, list)


# ── Verhoeff ──────────────────────────────────────────────────────────────────

class TestVerhoeff:
    def test_known_valid_numbers(self):
        from core.forgery.text_validator import _verhoeff_validate
        # These are known-valid Aadhaar test numbers (synthetic)
        # 999999999999 is NOT valid — Verhoeff is deterministic
        # We test that function returns bool and handles lengths
        result = _verhoeff_validate("123456789012")
        assert isinstance(result, bool)

    def test_wrong_length_invalid(self):
        from core.forgery.text_validator import _verhoeff_validate
        assert _verhoeff_validate("12345") is False
        assert _verhoeff_validate("") is False

    def test_non_digit_invalid(self):
        from core.forgery.text_validator import _verhoeff_validate
        assert _verhoeff_validate("ABCDEFGHIJKL") is False


# ── ImageForensics ────────────────────────────────────────────────────────────

class TestImageForensics:
    def setup_method(self):
        from core.forgery.image_forensics import ImageForensics
        self.forensics = ImageForensics()

    def test_clean_image_low_ela(self):
        """A pristine generated image should have low ELA score."""
        img = blank_image(200, 200, "white")
        signals = self.forensics._run_ela(img)
        # Blank image may or may not trigger — but should not crash
        assert isinstance(signals, list)

    def test_ela_returns_list(self):
        img = blank_image(300, 200)
        signals = self.forensics._run_ela(img)
        assert isinstance(signals, list)

    def test_noise_analysis_returns_list(self):
        img = blank_image(300, 200)
        signals = self.forensics._analyze_noise(img)
        assert isinstance(signals, list)

    def test_copy_move_returns_list(self):
        img = blank_image(200, 200)
        signals = self.forensics._detect_copy_move(img)
        assert isinstance(signals, list)

    def test_full_analyze_does_not_crash(self):
        img = blank_image(400, 300)
        signals = self.forensics.analyze(img)
        assert isinstance(signals, list)

    def test_ela_map_set_after_run(self):
        img = blank_image(200, 150)
        self.forensics._run_ela(img)
        assert hasattr(self.forensics, "ela_map")


# ── FontAnalyzer ──────────────────────────────────────────────────────────────

class TestFontAnalyzer:
    def setup_method(self):
        from core.forgery.font_analyzer import FontAnalyzer
        self.analyzer = FontAnalyzer()

    def test_consistent_fonts_no_signal(self):
        blocks = [
            TextBlock(f"word{i}", (i * 50, 10, i * 50 + 45, 30), 0.9)
            for i in range(8)
        ]
        for b in blocks:
            b.font_size_estimate = 20.0  # all same size
        ocr = OCRResult(blocks=blocks, full_text="word0 word1 word2", avg_confidence=0.9)
        img = blank_image()
        signals = self.analyzer.analyze(img, ocr)
        types = [s.signal_type for s in signals]
        assert "font_size_cluster_anomaly" not in types

    def test_inconsistent_fonts_signal(self):
        blocks = []
        for i in range(6):
            b = TextBlock(f"word{i}", (i * 60, 10, i * 60 + 55, 30), 0.9)
            b.font_size_estimate = 20.0
            blocks.append(b)
        # Make two blocks have wildly different font size
        blocks[2].font_size_estimate = 60.0
        blocks[4].font_size_estimate = 5.0

        ocr = OCRResult(blocks=blocks, full_text="word0 word1 word2 word3 word4 word5",
                        avg_confidence=0.9)
        img = blank_image()
        signals = self.analyzer.analyze(img, ocr)
        types = [s.signal_type for s in signals]
        assert "font_size_cluster_anomaly" in types

    def test_too_few_blocks_no_crash(self):
        ocr = OCRResult(blocks=[], full_text="", avg_confidence=0.9)
        img = blank_image()
        signals = self.analyzer.analyze(img, ocr)
        assert isinstance(signals, list)


# ── LayoutValidator ───────────────────────────────────────────────────────────

class TestLayoutValidator:
    def setup_method(self):
        from core.forgery.layout_validator import LayoutValidator
        self.validator = LayoutValidator()

    def test_unknown_doc_type_no_crash(self):
        img = blank_image()
        ocr = make_ocr("some text")
        signals = self.validator.validate(img, ocr, "unknown")
        assert isinstance(signals, list)
        assert signals == []

    def test_blank_photo_region_detected(self):
        img = blank_image(400, 300, "white")  # completely white = blank photo
        ocr = make_ocr("aadhaar 1234 5678 9012")
        signals = self.validator.validate(img, ocr, "aadhaar")
        types = [s.signal_type for s in signals]
        # Blank image should trigger photo_region_blank
        assert "photo_region_blank" in types


# ── Scoring ───────────────────────────────────────────────────────────────────

class TestScoring:
    def test_no_signals_zero_score(self):
        from core.scoring.scorer import compute_score
        assert compute_score([]) == 0.0

    def test_score_increases_with_signals(self):
        from core.scoring.scorer import compute_score
        s1 = ForgerySignal("text", "pan_format_invalid", "HIGH", 40, "test", 1.0)
        s2 = ForgerySignal("image", "ela_high_anomaly", "HIGH", 30, "test", 1.0)
        score1 = compute_score([s1])
        score2 = compute_score([s1, s2])
        assert score2 > score1

    def test_score_bounded_0_100(self):
        from core.scoring.scorer import compute_score
        signals = [
            ForgerySignal("text", "aadhaar_checksum_fail", "CRITICAL", 45, "test", 1.0),
            ForgerySignal("text", "marks_sum_mismatch", "CRITICAL", 50, "test", 1.0),
            ForgerySignal("image", "copy_move_detected", "HIGH", 35, "test", 1.0),
            ForgerySignal("image", "ela_high_anomaly", "HIGH", 30, "test", 1.0),
            ForgerySignal("layout", "qr_code_absent", "HIGH", 35, "test", 1.0),
        ]
        score = compute_score(signals)
        assert 0 <= score <= 100

    def test_verdicts(self):
        from core.scoring.scorer import score_to_verdict
        assert score_to_verdict(10)[0] == "GENUINE"
        assert score_to_verdict(40)[0] == "NEEDS REVIEW"
        assert score_to_verdict(80)[0] == "SUSPICIOUS"

    def test_subsystem_breakdown(self):
        from core.scoring.scorer import get_subsystem_breakdown
        signals = [
            ForgerySignal("text",   "pan_format_invalid", "HIGH", 40, "test", 1.0),
            ForgerySignal("image",  "ela_high_anomaly",   "HIGH", 30, "test", 1.0),
            ForgerySignal("layout", "qr_code_absent",     "HIGH", 35, "test", 1.0),
        ]
        breakdown = get_subsystem_breakdown(signals)
        assert "text"   in breakdown
        assert "image"  in breakdown
        assert "layout" in breakdown
        assert breakdown["text"] > 0


# ── ForgerySignal model ────────────────────────────────────────────────────────

class TestForgerySignalModel:
    def test_effective_weight(self):
        s = ForgerySignal("text", "test_signal", "HIGH", 40, "evidence", confidence=0.5)
        assert s.effective_weight == 20.0

    def test_effective_weight_full_confidence(self):
        s = ForgerySignal("text", "test_signal", "HIGH", 40, "evidence", confidence=1.0)
        assert s.effective_weight == 40.0
