"""
tests/test_classifier.py
Unit tests for document classification layer.
Run with: pytest tests/test_classifier.py -v
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ocr.result_models import OCRResult, TextBlock
from core.classifier.doc_classifier import classify_document, fuzzy_match, normalize


def make_ocr_result(text: str) -> OCRResult:
    blocks = [TextBlock(text=word, bbox=(0, 0, 100, 20), confidence=0.9)
              for word in text.split()]
    return OCRResult(blocks=blocks, full_text=text, avg_confidence=0.9)


class TestNormalize:
    def test_strips_whitespace(self):
        assert normalize("  Hello  ") == "hello"

    def test_lowercases(self):
        assert normalize("AADHAAR") == "aadhaar"

    def test_unicode_nfc(self):
        # Should not raise; Kannada text normalised
        result = normalize("ಆಧಾರ್")
        assert len(result) > 0


class TestFuzzyMatch:
    def test_exact_match(self):
        assert fuzzy_match("aadhaar", "this is an aadhaar card", threshold=85) is True

    def test_ocr_corruption(self):
        # OCR may turn 'AADHAAR' into 'AADHA4R'
        assert fuzzy_match("aadhaar", "AADHA4R number", threshold=75) is True

    def test_no_match(self):
        assert fuzzy_match("aadhaar", "permanent account number income tax", threshold=85) is False


class TestClassifyDocument:
    def test_aadhaar_classification(self):
        text = (
            "Unique Identification Authority of India  "
            "AADHAAR  1234 5678 9012  "
            "DOB: 01/01/1990  Address: 123 Main Street"
        )
        result = classify_document(make_ocr_result(text))
        assert result.doc_type == "aadhaar"
        assert result.confidence > 0.5

    def test_pan_classification(self):
        text = (
            "Income Tax Department Government of India  "
            "Permanent Account Number  ABCDE1234F  "
            "Name: John Doe  Date of Birth: 01/01/1985"
        )
        result = classify_document(make_ocr_result(text))
        assert result.doc_type == "pan"
        assert result.confidence > 0.5

    def test_sslc_classification(self):
        text = (
            "Karnataka Secondary Education Examination Board KSEEB  "
            "SSLC Certificate Register Number 12-34-567890  "
            "Mathematics 95 Science 88 Total Marks 450"
        )
        result = classify_document(make_ocr_result(text))
        assert result.doc_type == "sslc"
        assert result.confidence > 0.4

    def test_unknown_classification(self):
        text = "Hello World this is some random text with no document keywords"
        result = classify_document(make_ocr_result(text))
        assert result.doc_type == "unknown"
        assert result.reliable is False

    def test_aadhaar_pattern_alone_sufficient(self):
        # Even without keywords, 12-digit pattern should push score high enough
        text = "some text 1234 5678 9012 more text"
        result = classify_document(make_ocr_result(text))
        # Pattern alone gives 40 pts which exceeds MIN_CLASSIFICATION_SCORE=30
        assert result.doc_type == "aadhaar"

    def test_pan_pattern_alone_sufficient(self):
        text = "ABCDE1234F"
        result = classify_document(make_ocr_result(text))
        assert result.doc_type == "pan"

    def test_signals_populated(self):
        text = "AADHAAR UIDAI 1234 5678 9012"
        result = classify_document(make_ocr_result(text))
        assert len(result.signals) > 0

    def test_scores_dict_populated(self):
        text = "Permanent Account Number ABCDE1234F Income Tax"
        result = classify_document(make_ocr_result(text))
        assert "pan" in result.scores
        assert result.scores["pan"] > 0

    def test_multilingual_aadhaar(self):
        text = "आधार 1234 5678 9012 UIDAI भारत"
        result = classify_document(make_ocr_result(text))
        assert result.doc_type == "aadhaar"
