"""
core/explainability/heatmap.py
Generates an annotated PIL Image overlaying forgery signal locations.
Also produces ELA visualisation for side-by-side display.
"""
import logging
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.forgery.signal_models import ForgerySignal

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "CRITICAL": (231, 76,  60,  180),   # red
    "HIGH":     (230, 126, 34,  160),   # orange
    "MEDIUM":   (241, 196, 15,  130),   # yellow
    "LOW":      (52,  152, 219, 100),   # blue
}


def draw_annotated_image(
    image: Image.Image,
    signals: List[ForgerySignal],
    max_display: int = 8,
) -> Image.Image:
    """
    Overlay bounding boxes for spatial signals on a copy of the image.

    Returns an annotated PIL Image.
    """
    annotated = image.convert("RGBA").copy()
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    spatial_signals = [s for s in signals if s.location is not None]
    spatial_signals = sorted(spatial_signals, key=lambda s: -s.effective_weight)[:max_display]

    for signal in spatial_signals:
        loc = signal.location
        # Normalise location to (x1, y1, x2, y2)
        if isinstance(loc, (list, tuple)) and len(loc) == 4 and not isinstance(loc[0], tuple):
            bbox = tuple(int(v) for v in loc)
        else:
            continue

        color = SEVERITY_COLORS.get(signal.severity, (200, 200, 200, 120))
        draw.rectangle(bbox, outline=color[:3] + (230,), width=3)
        draw.rectangle(
            [bbox[0], bbox[1], bbox[2], min(bbox[1] + 22, bbox[3])],
            fill=color[:3] + (180,),
        )

        label = signal.signal_type.replace("_", " ").title()[:28]
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((bbox[0] + 4, bbox[1] + 3), label, fill=(255, 255, 255, 255), font=font)

    composite = Image.alpha_composite(annotated, overlay)
    return composite.convert("RGB")


def generate_ela_image(
    ela_map: Optional[np.ndarray],
    image_size: Tuple[int, int],
    amplify: float = 10.0,
) -> Optional[Image.Image]:
    """
    Convert raw ELA difference array → displayable PIL Image.

    ela_map: 2D float array of per-pixel mean absolute differences.
    """
    if ela_map is None:
        return None
    try:
        amplified = np.clip(ela_map * amplify, 0, 255).astype(np.uint8)
        ela_img = Image.fromarray(amplified, mode="L").convert("RGB")
        # Resize to match original image size for side-by-side display
        ela_img = ela_img.resize(image_size, Image.LANCZOS)
        return ela_img
    except Exception as exc:
        logger.warning("ELA image generation failed: %s", exc)
        return None


def build_confidence_heatmap_image(
    image: Image.Image,
    signals: List[ForgerySignal],
) -> Image.Image:
    """
    Create a simple colour-coded heatmap overlay showing subsystem
    contributions spatially (for the dashboard radar/heatmap display).
    """
    w, h = image.size
    heatmap = np.zeros((h, w), dtype=np.float32)

    for signal in signals:
        if signal.location is None:
            continue
        loc = signal.location
        if not (isinstance(loc, (list, tuple)) and len(loc) == 4 and
                not isinstance(loc[0], tuple)):
            continue
        x1, y1, x2, y2 = int(loc[0]), int(loc[1]), int(loc[2]), int(loc[3])
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        weight = signal.effective_weight
        heatmap[y1:y2, x1:x2] += weight

    if heatmap.max() > 0:
        heatmap /= heatmap.max()

    # Convert to RGBA heatmap
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = (heatmap * 255).astype(np.uint8)   # red channel
    rgba[:, :, 3] = (heatmap * 180).astype(np.uint8)   # alpha

    overlay = Image.fromarray(rgba, mode="RGBA")
    base = image.convert("RGBA")
    result = Image.alpha_composite(base, overlay)
    return result.convert("RGB")
