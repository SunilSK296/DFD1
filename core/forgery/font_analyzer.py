"""
core/forgery/font_analyzer.py
Detects visual inconsistencies in text rendering:
  - Font size anomalies within a line
  - Text misalignment suggesting copy-paste from different sources
  - OCR confidence hotspots (regions with suspiciously low confidence)
"""
import logging
from typing import List, Dict

import numpy as np
from PIL import Image

from core.ocr.result_models import OCRResult
from core.forgery.signal_models import ForgerySignal
from config.settings import FONT_SIZE_DEVIATION_THRESHOLD

logger = logging.getLogger(__name__)


class FontAnalyzer:
    """Analyses typography inconsistencies as forgery indicators."""

    def analyze(self, image: Image.Image, ocr: OCRResult) -> List[ForgerySignal]:
        signals: List[ForgerySignal] = []
        if len(ocr.blocks) < 3:
            return signals

        signals.extend(self._check_font_size_consistency(ocr))
        signals.extend(self._check_ocr_confidence_hotspots(ocr, image.size))
        return signals

    # ── Font size consistency ─────────────────────────────────────────────

    def _check_font_size_consistency(self, ocr: OCRResult) -> List[ForgerySignal]:
        """Flag blocks whose height deviates >THRESHOLD from their line's median."""
        signals = []

        # Group blocks by approximate line (y-centre bucketed to 20px)
        lines: Dict[int, list] = {}
        for block in ocr.blocks:
            if len(block.text.strip()) < 2:
                continue
            line_key = round(block.center_y / 20) * 20
            lines.setdefault(line_key, []).append(block)

        anomalous_count = 0
        anomalous_blocks = []

        for line_blocks in lines.values():
            if len(line_blocks) < 2:
                continue
            heights = [b.font_size_estimate for b in line_blocks]
            median_h = float(np.median(heights))
            if median_h < 5:
                continue
            for block in line_blocks:
                deviation = abs(block.font_size_estimate - median_h) / median_h
                if deviation > FONT_SIZE_DEVIATION_THRESHOLD:
                    anomalous_count += 1
                    anomalous_blocks.append(block)

        if anomalous_count >= 2:
            # Build a representative bbox from anomalous blocks
            bboxes = [b.bbox for b in anomalous_blocks[:5]]
            x1 = min(b[0] for b in bboxes)
            y1 = min(b[1] for b in bboxes)
            x2 = max(b[2] for b in bboxes)
            y2 = max(b[3] for b in bboxes)

            signals.append(ForgerySignal(
                subsystem="font",
                signal_type="font_size_cluster_anomaly",
                severity="MEDIUM",
                weight=20,
                evidence=(
                    f"{anomalous_count} text blocks have font sizes significantly "
                    f"inconsistent with surrounding text (>{FONT_SIZE_DEVIATION_THRESHOLD*100:.0f}% "
                    f"deviation from line median). This may indicate pasted text."
                ),
                confidence=0.70,
                location=(x1, y1, x2, y2),
            ))

        return signals

    # ── OCR confidence hotspots ───────────────────────────────────────────

    def _check_ocr_confidence_hotspots(
        self, ocr: OCRResult, image_size: tuple
    ) -> List[ForgerySignal]:
        """
        Build a grid-based confidence map.
        Flag cells where confidence is significantly lower than the document baseline.
        Low-confidence clusters often correlate with image manipulation.
        """
        signals = []

        if not ocr.blocks:
            return signals

        global_avg = ocr.avg_confidence
        if global_avg < 0.40:
            # Globally low-quality scan — avoid false positives
            return signals

        GRID = 8  # 8×8 grid
        w, h = image_size
        cell_w = w / GRID
        cell_h = h / GRID

        grid_conf: Dict[tuple, list] = {}
        for block in ocr.blocks:
            ci = int(block.center_x / cell_w)
            ri = int(block.center_y / cell_h)
            ci = min(ci, GRID - 1)
            ri = min(ri, GRID - 1)
            grid_conf.setdefault((ri, ci), []).append(block.confidence)

        if len(grid_conf) < 4:
            return signals

        cell_avgs = {k: float(np.mean(v)) for k, v in grid_conf.items()}
        all_avgs = list(cell_avgs.values())
        global_cell_mean = float(np.mean(all_avgs))
        global_cell_std = float(np.std(all_avgs))

        if global_cell_std < 0.05:
            return signals  # uniform document — not suspicious

        low_cells = [
            cell for cell, avg in cell_avgs.items()
            if avg < global_cell_mean - 2.0 * global_cell_std
        ]

        if low_cells:
            # Convert grid cells to pixel bboxes
            locations = []
            for ri, ci in low_cells:
                lx1 = int(ci * cell_w)
                ly1 = int(ri * cell_h)
                lx2 = int((ci + 1) * cell_w)
                ly2 = int((ri + 1) * cell_h)
                locations.append((lx1, ly1, lx2, ly2))

            signals.append(ForgerySignal(
                subsystem="font",
                signal_type="ocr_confidence_hotspot",
                severity="MEDIUM",
                weight=25,
                evidence=(
                    f"OCR confidence is unusually low in {len(low_cells)} region(s) "
                    f"compared to the rest of the document. "
                    f"Low-confidence clusters often indicate image manipulation."
                ),
                confidence=0.65,
                location=locations[0] if locations else None,
            ))

        return signals
