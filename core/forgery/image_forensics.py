"""
core/forgery/image_forensics.py
ELA (Error Level Analysis), noise inconsistency, and copy-move detection.
These are image-level signals independent of OCR quality.
"""
import io
import logging
from typing import List, Tuple

import numpy as np
from PIL import Image

from core.forgery.signal_models import ForgerySignal
from config.settings import ELA_COMPARISON_QUALITY, ELA_MAX_DIMENSION, ELA_STD_MULTIPLIER

logger = logging.getLogger(__name__)


def _resize_for_ela(image: Image.Image) -> Image.Image:
    """Resize image to ELA_MAX_DIMENSION for faster processing."""
    w, h = image.size
    if max(w, h) > ELA_MAX_DIMENSION:
        scale = ELA_MAX_DIMENSION / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return image


class ImageForensics:
    """ELA + noise + copy-move forensic analysis."""

    def analyze(self, image: Image.Image) -> List[ForgerySignal]:
        signals: List[ForgerySignal] = []
        try:
            signals.extend(self._run_ela(image))
        except Exception as exc:
            logger.warning("ELA failed: %s", exc)
        try:
            signals.extend(self._analyze_noise(image))
        except Exception as exc:
            logger.warning("Noise analysis failed: %s", exc)
        # try:
        #     signals.extend(self._detect_copy_move(image))
        # except Exception as exc:
        #     logger.warning("Copy-move detection failed: %s", exc)
        # return signals

    # ── ELA ───────────────────────────────────────────────────────────────

    def _run_ela(self, image: Image.Image) -> List[ForgerySignal]:
        """
        Error Level Analysis:
        1. Re-save as JPEG at reduced quality.
        2. Diff original vs re-saved, amplify × 10.
        3. Flag grid cells with ELA significantly above document baseline.
        """
        signals = []

        ela_img = _resize_for_ela(image.convert("RGB"))
        w, h = ela_img.size

        # Save at reduced quality
        buffer = io.BytesIO()
        ela_img.save(buffer, format="JPEG", quality=ELA_COMPARISON_QUALITY)
        buffer.seek(0)
        recompressed = Image.open(buffer).convert("RGB")

        original_arr = np.array(ela_img, dtype=np.float32)
        recomp_arr = np.array(recompressed, dtype=np.float32)
        ela_arr = np.abs(original_arr - recomp_arr).mean(axis=2)  # grayscale diff

        # Grid analysis
        GRID = 8
        cell_w = w // GRID
        cell_h = h // GRID

        cell_means = []
        for ri in range(GRID):
            for ci in range(GRID):
                cell = ela_arr[ri*cell_h:(ri+1)*cell_h, ci*cell_w:(ci+1)*cell_w]
                cell_means.append(float(cell.mean()))

        if not cell_means:
            return signals

        global_mean = float(np.mean(cell_means))
        global_std = float(np.std(cell_means))

        # Calibration: if >40% cells are "medium" ELA, it's a scan artifact — raise threshold
        medium_count = sum(1 for m in cell_means if m > 8)
        if medium_count / len(cell_means) > 0.4:
            # Noisy scan — raise bar
            effective_multiplier = ELA_STD_MULTIPLIER * 1.5
        else:
            effective_multiplier = ELA_STD_MULTIPLIER

        threshold = global_mean + effective_multiplier * global_std
        high_cells = []

        idx = 0
        for ri in range(GRID):
            for ci in range(GRID):
                if cell_means[idx] > threshold and threshold > 5:
                    lx1 = ci * cell_w
                    ly1 = ri * cell_h
                    lx2 = (ci + 1) * cell_w
                    ly2 = (ri + 1) * cell_h
                    high_cells.append((lx1, ly1, lx2, ly2, cell_means[idx]))
                idx += 1

        if len(high_cells) >= 2:
            severity = "HIGH" if len(high_cells) >= 4 else "MEDIUM"
            weight = 30 if severity == "HIGH" else 15
            locs = [(c[0], c[1], c[2], c[3]) for c in high_cells]
            signals.append(ForgerySignal(
                subsystem="image",
                signal_type="ela_high_anomaly" if severity == "HIGH" else "ela_medium_anomaly",
                severity=severity,
                weight=weight,
                evidence=(
                    f"Error Level Analysis detected compression inconsistencies in "
                    f"{len(high_cells)} region(s). Edited areas retain different "
                    f"compression levels than the surrounding image."
                ),
                confidence=0.72,
                location=locs[0],
            ))

            # Store ELA map as attribute for heatmap rendering
            self.ela_map = ela_arr
            self.ela_suspicious_regions = locs
        else:
            self.ela_map = ela_arr
            self.ela_suspicious_regions = []

        return signals

    # ── Noise analysis ────────────────────────────────────────────────────

    def _analyze_noise(self, image: Image.Image) -> List[ForgerySignal]:
        """
        Estimate local noise per image quadrant.
        Inconsistent noise levels suggest image compositing.
        """
        signals = []

        gray = np.array(image.convert("L"), dtype=np.float32)
        h, w = gray.shape

        mid_h, mid_w = h // 2, w // 2
        quadrants = {
            "top-left":     gray[:mid_h, :mid_w],
            "top-right":    gray[:mid_h, mid_w:],
            "bottom-left":  gray[mid_h:, :mid_w],
            "bottom-right": gray[mid_h:, mid_w:],
        }

        # Laplacian variance as noise proxy
        from PIL import ImageFilter

        noise_levels = {}
        for name, quad in quadrants.items():
            if quad.size == 0:
                continue
            lap = np.abs(
                quad[:-1, :-1] - quad[:-1, 1:] - quad[1:, :-1] + quad[1:, 1:]
            )
            noise_levels[name] = float(np.var(lap))

        if len(noise_levels) < 3:
            return signals

        vals = list(noise_levels.values())
        mean_noise = float(np.mean(vals))
        std_noise = float(np.std(vals))

        if mean_noise < 1.0 or std_noise < 0.5:
            return signals  # very clean or uniform image

        outliers = [
            name for name, lvl in noise_levels.items()
            if abs(lvl - mean_noise) > 2.0 * std_noise
        ]

        if outliers:
            signals.append(ForgerySignal(
                subsystem="image",
                signal_type="noise_inconsistency",
                severity="MEDIUM",
                weight=20,
                evidence=(
                    f"Noise level is significantly inconsistent in {', '.join(outliers)} "
                    f"region(s) compared to the rest of the document. "
                    f"This may indicate image compositing (pasting from multiple sources)."
                ),
                confidence=0.65,
            ))

        return signals

    # ── Copy-move detection ───────────────────────────────────────────────

    def _detect_copy_move(self, image: Image.Image) -> List[ForgerySignal]:
        """
        Detect copy-moved regions using DCT-based patch hashing.
        Flags if ≥3 non-adjacent patches are identical.
        """
        signals = []

        try:
            import cv2

            gray = np.array(image.convert("L"), dtype=np.float32)
            h, w = gray.shape

            PATCH = 16
            STEP = 8  # overlapping patches

            hashes = {}
            for y in range(0, h - PATCH, STEP):
                for x in range(0, w - PATCH, STEP):
                    patch = gray[y:y+PATCH, x:x+PATCH]
                    dct = cv2.dct(patch)
                    # Use top-left 4×4 DCT coefficients as hash
                    coeff = dct[:4, :4].flatten().astype(np.int16)
                    key = tuple(coeff)
                    hashes.setdefault(key, []).append((x, y))

            # Find duplicates that are spatially far apart (not just adjacent)
            duplicate_groups = []
            for key, positions in hashes.items():
                if len(positions) < 2:
                    continue
                # Check distance between copies
                far_pairs = []
                for i, (x1, y1) in enumerate(positions):
                    for x2, y2 in positions[i+1:]:
                        dist = ((x2-x1)**2 + (y2-y1)**2) ** 0.5
                        if dist > PATCH * 3:
                            far_pairs.append(((x1, y1), (x2, y2)))
                if len(far_pairs) >= 2:
                    duplicate_groups.append(far_pairs)

            if len(duplicate_groups) >= 3:
                signals.append(ForgerySignal(
                    subsystem="image",
                    signal_type="copy_move_detected",
                    severity="HIGH",
                    weight=35,
                    evidence=(
                        f"Copy-move forgery detected: {len(duplicate_groups)} groups of "
                        f"identical image patches found at different locations. "
                        f"This indicates regions of the image were duplicated."
                    ),
                    confidence=0.75,
                ))
        except ImportError:
            logger.debug("OpenCV not available — skipping copy-move detection.")
        except Exception as exc:
            logger.debug("Copy-move detection error: %s", exc)

        return signals
