"""
core/explainability/reason_templates.py
Maps signal_type → human-readable reason text.
This file is the entire "explainability layer's vocabulary".
Update here to improve all reason messages without touching logic code.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ── Reason templates ─────────────────────────────────────────────────────────
# Each key maps to a dict with: short, detail, severity, category
# Placeholders: {value}, {expected}, {delta}, {region}, {doc_type}

SIGNAL_TO_REASON: Dict[str, Dict[str, str]] = {
    # Text
    "aadhaar_checksum_fail": {
        "short":    "Aadhaar number fails mathematical checksum",
        "detail":   (
            "The Aadhaar number '{value}' fails the Verhoeff checksum algorithm "
            "that UIDAI embeds in every genuine Aadhaar number. "
            "This is a near-conclusive indicator of tampering or fabrication."
        ),
        "severity": "CRITICAL",
        "category": "Format Issues",
    },
    "aadhaar_number_not_found": {
        "short":    "No valid Aadhaar number pattern found",
        "detail":   (
            "A genuine Aadhaar card always contains a 12-digit number in "
            "XXXX XXXX XXXX format. No such pattern was detected in this document."
        ),
        "severity": "HIGH",
        "category": "Format Issues",
    },
    "pan_format_invalid": {
        "short":    "PAN number format is invalid",
        "detail":   (
            "Expected PAN format: five uppercase letters, four digits, one uppercase letter "
            "(e.g. ABCDE1234F). No valid PAN number was found. "
            "The number may have been manually altered."
        ),
        "severity": "HIGH",
        "category": "Format Issues",
    },
    "pan_category_invalid": {
        "short":    "PAN number contains invalid entity category code",
        "detail":   (
            "The 4th character of a PAN number encodes the entity type "
            "(P=Individual, C=Company, H=HUF, etc.). "
            "The detected value '{value}' uses an unrecognised category code."
        ),
        "severity": "MEDIUM",
        "category": "Format Issues",
    },
    "marks_sum_mismatch": {
        "short":    "Total marks do not match sum of subject marks",
        "detail":   (
            "Sum of individual subject marks detected: {value}. "
            "Printed total on certificate: {expected}. "
            "A discrepancy in marks is a strong indicator of certificate tampering."
        ),
        "severity": "CRITICAL",
        "category": "Logical Inconsistencies",
    },
    "required_field_missing": {
        "short":    "Required field '{value}' not found",
        "detail":   (
            "Genuine documents of this type always contain a '{value}' field. "
            "Its absence may indicate the document is incomplete, cropped, or fabricated."
        ),
        "severity": "MEDIUM",
        "category": "Format Issues",
    },
    "pincode_invalid": {
        "short":    "Pincode format appears invalid",
        "detail":   (
            "The pincode '{value}' found in the address field does not conform to the "
            "Indian 6-digit pincode format (first digit 1–9)."
        ),
        "severity": "LOW",
        "category": "Logical Inconsistencies",
    },
    # Layout
    "qr_code_absent": {
        "short":    "QR code missing from expected location",
        "detail":   (
            "Authentic {doc_type} documents contain a QR code (encoding digitally signed data) "
            "in the lower-right region. No QR code was detected. "
            "Its absence is a strong indicator of a fake or photocopied document."
        ),
        "severity": "HIGH",
        "category": "Layout Issues",
    },
    "qr_region_misplaced": {
        "short":    "QR code found in unexpected position",
        "detail":   (
            "A QR code was detected but not in its expected location. "
            "Genuine documents follow a fixed template; positional deviation suggests "
            "the document may have been assembled from different sources."
        ),
        "severity": "MEDIUM",
        "category": "Layout Issues",
    },
    "photo_region_blank": {
        "short":    "Photo region appears blank or missing",
        "detail":   (
            "The area where a photograph should appear shows uniform pixel values. "
            "This may indicate the photo was removed, obscured, or was never present."
        ),
        "severity": "MEDIUM",
        "category": "Layout Issues",
    },
    "text_alignment_broken": {
        "short":    "Text alignment is inconsistent across the document",
        "detail":   (
            "Multiple rows of text have inconsistent vertical alignment. "
            "Genuine printed documents maintain uniform alignment; "
            "misalignment suggests text was digitally inserted from different sources."
        ),
        "severity": "MEDIUM",
        "category": "Layout Issues",
    },
    # Font / Visual
    "font_size_cluster_anomaly": {
        "short":    "Font size inconsistencies detected",
        "detail":   (
            "Several text blocks have font sizes significantly different from surrounding text "
            "on the same line. This is a common artefact of pasting edited text "
            "into an existing document image."
        ),
        "severity": "MEDIUM",
        "category": "Visual Anomalies",
    },
    "ocr_confidence_hotspot": {
        "short":    "Low OCR confidence in specific regions (possible tampering)",
        "detail":   (
            "OCR confidence is unusually low in certain regions compared to the rest of the "
            "document. Manipulated areas often have degraded print quality due to "
            "resaving or compositing artefacts."
        ),
        "severity": "MEDIUM",
        "category": "Visual Anomalies",
    },
    # Image Forensics
    "ela_high_anomaly": {
        "short":    "Image editing artefacts detected (Error Level Analysis)",
        "detail":   (
            "Error Level Analysis found significant compression inconsistencies in "
            "multiple regions. Areas that have been digitally edited retain different "
            "JPEG compression levels than the original scan, making them stand out clearly."
        ),
        "severity": "HIGH",
        "category": "Visual Anomalies",
    },
    "ela_medium_anomaly": {
        "short":    "Minor image editing artefacts detected",
        "detail":   (
            "Error Level Analysis detected minor compression inconsistencies. "
            "This may indicate light editing or could be a scanning artefact. "
            "Consider alongside other signals."
        ),
        "severity": "MEDIUM",
        "category": "Visual Anomalies",
    },
    "copy_move_detected": {
        "short":    "Copy-move forgery detected",
        "detail":   (
            "Identical image patches were found at multiple different locations in the document. "
            "This is a hallmark of copy-move forgery, where a region is duplicated to "
            "cover or replace original content."
        ),
        "severity": "HIGH",
        "category": "Visual Anomalies",
    },
    "noise_inconsistency": {
        "short":    "Noise level inconsistent across document regions",
        "detail":   (
            "The image noise pattern varies significantly between quadrants of the document. "
            "Genuine scanned documents have uniform noise; inconsistency suggests "
            "different image regions originate from different sources."
        ),
        "severity": "MEDIUM",
        "category": "Visual Anomalies",
    },
}

CATEGORY_ORDER = [
    "Format Issues",
    "Logical Inconsistencies",
    "Layout Issues",
    "Visual Anomalies",
]

# ── Report dataclass ─────────────────────────────────────────────────────────

@dataclass
class Reason:
    short: str
    detail: str
    severity: str
    category: str
    signal_type: str
    subsystem: str
    location: Optional[Any] = None


@dataclass
class Report:
    verdict: str                                    # GENUINE / NEEDS REVIEW / SUSPICIOUS
    verdict_color: str                              # hex colour for UI
    confidence_score: float                         # 0–100
    doc_type: str
    doc_type_confidence: float
    reasons: List[Reason] = field(default_factory=list)
    grouped_reasons: Dict[str, List[Reason]] = field(default_factory=dict)
    top_reason: Optional[Reason] = None
    subsystem_scores: Dict[str, float] = field(default_factory=dict)
    ela_map: Optional[Any] = None                  # numpy array for heatmap
    ela_regions: List[Any] = field(default_factory=list)
    preprocessing_meta: Dict[str, Any] = field(default_factory=dict)
    classification_signals: List[str] = field(default_factory=list)
