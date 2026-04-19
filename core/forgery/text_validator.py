"""
core/forgery/text_validator.py
Pattern + logical consistency checks on OCR-extracted text.
"""
import logging
import re
from typing import List, Optional

from core.ocr.result_models import OCRResult
from core.forgery.signal_models import ForgerySignal

logger = logging.getLogger(__name__)

# ── Document-specific patterns ───────────────────────────────────────────────

PATTERNS = {
    "aadhaar": {
        "number": re.compile(r"\d{4}[\s\-]?\d{4}[\s\-]?\d{4}"),
        "number_strict": re.compile(r"^\d{4}[\s\-]\d{4}[\s\-]\d{4}$"),
    },
    "pan": {
        "number": re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]{1}"),
    },
    "sslc": {
        "register": re.compile(r"\d{2}-\d{2}-\d{6}|\d{7,10}"),
    },
}

# PAN 4th character → category
PAN_4TH_CHAR_CATEGORIES = {
    "P": "Individual",
    "C": "Company",
    "H": "HUF",
    "F": "Firm",
    "A": "AOP",
    "T": "Trust",
    "B": "BOI",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "G": "Government",
}

# ── Verhoeff algorithm for Aadhaar checksum ──────────────────────────────────

_VERHOEFF_D = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_VERHOEFF_P = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8],
]
_VERHOEFF_INV = [0,4,3,2,1,9,8,7,6,5]


def _verhoeff_validate(number: str) -> bool:
    """Return True if the Aadhaar number passes Verhoeff checksum."""
    try:
        digits = [int(d) for d in number if d.isdigit()]
        if len(digits) != 12:
            return False
        c = 0
        for i, digit in enumerate(reversed(digits)):
            c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
        return c == 0
    except Exception:
        return False


class TextValidator:
    """Runs pattern and logical consistency checks on OCR text."""

    def validate(self, ocr: OCRResult, doc_type: str) -> List[ForgerySignal]:
        signals: List[ForgerySignal] = []
        signals.extend(self._validate_patterns(ocr, doc_type))
        signals.extend(self._validate_logical_consistency(ocr, doc_type))
        signals.extend(self._validate_field_presence(ocr, doc_type))
        return signals

    # ── Pattern validation ────────────────────────────────────────────────

    def _validate_patterns(self, ocr: OCRResult, doc_type: str) -> List[ForgerySignal]:
        signals = []
        text = ocr.full_text
        text_upper = text.upper()

        if doc_type == "aadhaar":
            number = self._extract_aadhaar_number(text)
            if number is None:
                signals.append(ForgerySignal(
                    subsystem="text",
                    signal_type="aadhaar_number_not_found",
                    severity="HIGH",
                    weight=30,
                    evidence="No 12-digit Aadhaar number pattern found in document.",
                    confidence=0.9,
                ))
            else:
                # Verhoeff checksum
                digits = re.sub(r"\D", "", number)
                if not _verhoeff_validate(digits):
                    signals.append(ForgerySignal(
                        subsystem="text",
                        signal_type="aadhaar_checksum_fail",
                        severity="CRITICAL",
                        weight=45,
                        evidence=f"Aadhaar number '{number}' fails Verhoeff checksum. "
                                 f"Genuine Aadhaar numbers always satisfy this mathematical check.",
                        confidence=0.95,
                        value=number,
                    ))

        elif doc_type == "pan":
            pan_match = PATTERNS["pan"]["number"].search(text_upper)
            if pan_match is None:
                signals.append(ForgerySignal(
                    subsystem="text",
                    signal_type="pan_format_invalid",
                    severity="HIGH",
                    weight=40,
                    evidence="No valid PAN number (format AAAAA9999A) found in document.",
                    confidence=0.9,
                ))
            else:
                pan = pan_match.group()
                # 4th char should be a valid category
                if len(pan) >= 4 and pan[3] not in PAN_4TH_CHAR_CATEGORIES:
                    signals.append(ForgerySignal(
                        subsystem="text",
                        signal_type="pan_category_invalid",
                        severity="MEDIUM",
                        weight=20,
                        evidence=f"PAN 4th character '{pan[3]}' is not a recognised entity category.",
                        confidence=0.85,
                        value=pan,
                    ))

        return signals

    # ── Logical consistency ───────────────────────────────────────────────

    def _validate_logical_consistency(self, ocr: OCRResult, doc_type: str) -> List[ForgerySignal]:
        signals = []

        if doc_type == "sslc":
            signals.extend(self._check_sslc_marks(ocr))

        if doc_type == "aadhaar":
            signals.extend(self._check_pincode(ocr))

        return signals

    def _check_sslc_marks(self, ocr: OCRResult) -> List[ForgerySignal]:
        """
        Try to extract subject marks and verify they sum to the stated total.
        """
        signals = []
        text = ocr.full_text

        # Look for lines with subject + marks pattern: "Mathematics 95" or "95/100"
        mark_pattern = re.compile(r"\b(\d{1,3})\s*/\s*100\b|\b(\d{1,3})\b")
        numbers = [int(m.group(1) or m.group(2)) for m in mark_pattern.finditer(text)
                   if 0 <= int(m.group(1) or m.group(2)) <= 100]

        # Look for "Total" near a number
        total_match = re.search(r"total[\s:]+(\d{2,4})", text, re.IGNORECASE)
        if total_match and len(numbers) >= 5:
            stated_total = int(total_match.group(1))
            # Use numbers that are plausible subject marks (≤ 100)
            subject_marks = [n for n in numbers if 0 <= n <= 100][:8]
            computed_total = sum(subject_marks)

            if abs(computed_total - stated_total) > 5:  # 5-mark tolerance for OCR errors
                signals.append(ForgerySignal(
                    subsystem="text",
                    signal_type="marks_sum_mismatch",
                    severity="CRITICAL" if abs(computed_total - stated_total) > 20 else "MEDIUM",
                    weight=50,
                    evidence=(
                        f"Sum of detected subject marks ({computed_total}) does not match "
                        f"printed total ({stated_total}). "
                        f"Difference: {abs(computed_total - stated_total)} marks."
                    ),
                    confidence=0.75,
                    value=str(computed_total),
                    expected=str(stated_total),
                ))

        return signals

    def _check_pincode(self, ocr: OCRResult) -> List[ForgerySignal]:
        """Validate Indian pincode format in Aadhaar."""
        signals = []
        text = ocr.full_text

        pincode_match = re.search(r"\b([1-9][0-9]{5})\b", text)
        if pincode_match:
            pincode = pincode_match.group(1)
            # Very basic: first digit must be 1–9 (already enforced), length 6
            if len(pincode) != 6:
                signals.append(ForgerySignal(
                    subsystem="text",
                    signal_type="pincode_invalid",
                    severity="LOW",
                    weight=10,
                    evidence=f"Pincode '{pincode}' has invalid format.",
                    confidence=0.6,
                    value=pincode,
                ))
        return signals

    # ── Required fields ───────────────────────────────────────────────────

    def _validate_field_presence(self, ocr: OCRResult, doc_type: str) -> List[ForgerySignal]:
        signals = []
        text_lower = ocr.full_text.lower()

        field_keywords = {
            "aadhaar": {
                "name": ["name", "नाम", "ಹೆಸರು"],
                "dob": ["dob", "date of birth", "जन्म तिथि", "ಜನ್ಮ ದಿನಾಂಕ"],
                "number": [r"\d{4}[\s-]\d{4}[\s-]\d{4}"],
            },
            "pan": {
                "name": ["name", "नाम"],
                "dob": ["date of birth", "जन्म तिथि"],
                "number": [r"[A-Z]{5}[0-9]{4}[A-Z]"],
            },
            "sslc": {
                "register_number": ["register number", "reg no", "registration"],
                "name": ["name of candidate", "student name", "candidate name", "name"],
                "marks": ["marks", "total"],
            },
        }

        doc_fields = field_keywords.get(doc_type, {})
        for field_name, keywords in doc_fields.items():
            found = False
            for kw in keywords:
                if kw.startswith(r"\d") or kw.startswith("["):  # regex
                    if re.search(kw, ocr.full_text):
                        found = True
                        break
                elif kw in text_lower:
                    found = True
                    break
            if not found:
                signals.append(ForgerySignal(
                    subsystem="text",
                    signal_type="required_field_missing",
                    severity="MEDIUM",
                    weight=20,
                    evidence=f"Expected field '{field_name}' not found in document.",
                    confidence=0.7,
                    value=field_name,
                ))
        return signals

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_aadhaar_number(text: str) -> Optional[str]:
        """Return first Aadhaar-like 12-digit number found in text."""
        # Try spaced/hyphenated first
        m = re.search(r"\d{4}[\s\-]\d{4}[\s\-]\d{4}", text)
        if m:
            return m.group()
        # Fallback: bare 12 digits
        m = re.search(r"\b\d{12}\b", text)
        return m.group() if m else None
