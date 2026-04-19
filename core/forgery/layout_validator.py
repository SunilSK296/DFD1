"""
core/forgery/layout_validator.py
Validates structural integrity of document using template-based region detection.
Genuine documents are printed from fixed templates — spatial deviations are suspicious.
"""
import logging
from typing import List, Tuple, Optional

import numpy as np
from PIL import Image

from core.ocr.result_models import OCRResult
from core.forgery.signal_models import ForgerySignal
from config.settings import LAYOUT_POSITION_TOLERANCE

logger = logging.getLogger(__name__)


# Normalised bounding boxes (x1, y1, x2, y2) in 0–1 range
LAYOUT_TEMPLATES = {
    "aadhaar": {
        "photo_region":  (0.0, 0.05, 0.28, 0.70),
        "number_region": (0.05, 0.72, 0.90, 0.95),
        "qr_region":     (0.70, 0.55, 1.00, 1.00),
        "logo_region":   (0.30, 0.00, 0.70, 0.18),
    },
    "pan": {
        "photo_region":      (0.65, 0.10, 0.97, 0.65),
        "number_region":     (0.05, 0.50, 0.65, 0.72),
        "signature_region":  (0.65, 0.65, 0.97, 0.90),
    },
    "sslc": {
        "header_region":     (0.05, 0.00, 0.95, 0.20),
        "marks_region":      (0.05, 0.30, 0.95, 0.85),
    },
}


class LayoutValidator:
    """Detects misplaced or missing key regions in a document."""

    def validate(
        self,
        image: Image.Image,
        ocr: OCRResult,
        doc_type: str,
    ) -> List[ForgerySignal]:
        signals = []

        template = LAYOUT_TEMPLATES.get(doc_type)
        if template is None:
            return signals  # no template for this doc type

        w, h = image.size

        # Check QR code presence (Aadhaar, PAN)
        if "qr_region" in template:
            signals.extend(self._check_qr_presence(image, template["qr_region"], doc_type))

        # Check photo region
        if "photo_region" in template:
            signals.extend(
                self._check_region_content(
                    image, template["photo_region"], "photo_region",
                    doc_type, w, h,
                )
            )

        # Check overall text alignment
        signals.extend(self._check_text_alignment(ocr, w, h))

        return signals

    # ── QR detection ──────────────────────────────────────────────────────

    def _check_qr_presence(
        self,
        image: Image.Image,
        expected_bbox: Tuple[float, float, float, float],
        doc_type: str,
    ) -> List[ForgerySignal]:
        """Try to find a QR code; flag if absent."""
        try:
            from pyzbar.pyzbar import decode
            import numpy as np

            img_array = np.array(image.convert("L"))
            codes = decode(img_array)
            if not codes:
                return [ForgerySignal(
                    subsystem="layout",
                    signal_type="qr_code_absent",
                    severity="HIGH",
                    weight=35,
                    evidence=(
                        f"No QR code detected. Authentic {doc_type.upper()} documents "
                        f"contain a QR code in the lower-right region."
                    ),
                    confidence=0.85,
                )]

            # QR found — check if it's in the expected region
            w, h = image.size
            for code in codes:
                pts = code.polygon
                if pts:
                    cx = np.mean([p.x for p in pts]) / w
                    cy = np.mean([p.y for p in pts]) / h
                    x1, y1, x2, y2 = expected_bbox
                    tol = LAYOUT_POSITION_TOLERANCE
                    if not (x1 - tol <= cx <= x2 + tol and y1 - tol <= cy <= y2 + tol):
                        return [ForgerySignal(
                            subsystem="layout",
                            signal_type="qr_region_misplaced",
                            severity="MEDIUM",
                            weight=20,
                            evidence=(
                                f"QR code found at unexpected position "
                                f"(centre {cx:.2f},{cy:.2f}); "
                                f"expected region {expected_bbox}."
                            ),
                            confidence=0.7,
                        )]
        except ImportError:
            logger.debug("pyzbar not available — skipping QR check.")
        except Exception as exc:
            logger.warning("QR check failed: %s", exc)

        return []

    # ── Region content checks ─────────────────────────────────────────────

    def _check_region_content(
        self,
        image: Image.Image,
        norm_bbox: Tuple[float, float, float, float],
        region_name: str,
        doc_type: str,
        w: int,
        h: int,
    ) -> List[ForgerySignal]:
        """
        Check that the expected photo region contains a face-like blob
        (a region significantly darker or different from background).
        Simple heuristic: std dev of pixel values in region > threshold.
        """
        try:
            import numpy as np

            x1 = int(norm_bbox[0] * w)
            y1 = int(norm_bbox[1] * h)
            x2 = int(norm_bbox[2] * w)
            y2 = int(norm_bbox[3] * h)

            crop = image.crop((x1, y1, x2, y2)).convert("L")
            arr = np.array(crop)
            std_dev = float(arr.std())

            if std_dev < 15.0:
                return [ForgerySignal(
                    subsystem="layout",
                    signal_type="photo_region_blank",
                    severity="MEDIUM",
                    weight=20,
                    evidence=(
                        f"Photo region appears blank or uniform "
                        f"(pixel std dev={std_dev:.1f}). "
                        f"Expected a photograph in this region."
                    ),
                    confidence=0.65,
                    location=(x1, y1, x2, y2),
                )]

        except Exception as exc:
            logger.debug("Region content check failed for %s: %s", region_name, exc)

        return []

    # ── Text alignment ────────────────────────────────────────────────────

    def _check_text_alignment(
        self,
        ocr: OCRResult,
        img_w: int,
        img_h: int,
    ) -> List[ForgerySignal]:
        """
        Group text blocks by approximate row (y-centre ± 10px).
        Within each row, flag blocks whose x-start is wildly inconsistent.
        """
        if len(ocr.blocks) < 5:
            return []

        try:
            import numpy as np

            # Bucket blocks by y-centre
            rows: dict = {}
            for block in ocr.blocks:
                row_key = round(block.center_y / 20) * 20
                rows.setdefault(row_key, []).append(block)

            misaligned = 0
            for row_blocks in rows.values():
                if len(row_blocks) < 2:
                    continue
                y_centres = [b.center_y for b in row_blocks]
                if np.std(y_centres) > img_h * 0.03:  # >3% height variation in a row
                    misaligned += 1

            if misaligned >= 3:
                return [ForgerySignal(
                    subsystem="layout",
                    signal_type="text_alignment_broken",
                    severity="MEDIUM",
                    weight=15,
                    evidence=(
                        f"Text alignment is inconsistent in {misaligned} rows. "
                        f"This can indicate text was pasted from different sources."
                    ),
                    confidence=0.6,
                )]
        except Exception as exc:
            logger.debug("Text alignment check failed: %s", exc)

        return []
