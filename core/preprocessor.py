"""
core/preprocessor.py
Image preprocessing pipeline: deskew, denoise, contrast enhancement, resize.
Preprocessing quality has 10× more impact on accuracy than model choice.
"""
import logging
from typing import Tuple, Dict, Any

import numpy as np
from PIL import Image

from config.settings import MAX_IMAGE_DIMENSION

logger = logging.getLogger(__name__)


def preprocess(image: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Full preprocessing pipeline.

    Returns:
        (enhanced_PIL_Image, metadata_dict)
    """
    meta: Dict[str, Any] = {
        "original_size": image.size,
        "skew_angle": 0.0,
        "was_resized": False,
        "was_enhanced": False,
        "was_deskewed": False,
    }

    image = _fix_exif_orientation(image)
    image, meta["was_resized"] = _resize_to_standard(image, MAX_IMAGE_DIMENSION)
    image, meta["skew_angle"] = _deskew(image)
    if meta["skew_angle"] != 0.0:
        meta["was_deskewed"] = True
    image = _denoise(image)
    image = _enhance_contrast(image)
    meta["was_enhanced"] = True
    meta["final_size"] = image.size

    logger.debug("Preprocessing done: skew=%.1f°, size=%s", meta["skew_angle"], image.size)
    return image, meta


# ── Private helpers ──────────────────────────────────────────────────────────

def _fix_exif_orientation(image: Image.Image) -> Image.Image:
    """Rotate image according to EXIF orientation tag."""
    try:
        from PIL import ExifTags
        exif = image._getexif()  # type: ignore[attr-defined]
        if exif is None:
            return image
        orient_tag = next(
            (k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None
        )
        if orient_tag is None:
            return image
        orient = exif.get(orient_tag)
        rotations = {3: 180, 6: 270, 8: 90}
        if orient in rotations:
            return image.rotate(rotations[orient], expand=True)
    except Exception:
        pass
    return image


def _resize_to_standard(
    image: Image.Image, max_dim: int
) -> Tuple[Image.Image, bool]:
    """Resize so the largest dimension is at most max_dim pixels."""
    w, h = image.size
    if max(w, h) <= max_dim:
        return image, False
    scale = max_dim / max(w, h)
    new_size = (int(w * scale), int(h * scale))
    return image.resize(new_size, Image.LANCZOS), True


def _deskew(image: Image.Image) -> Tuple[Image.Image, float]:
    """
    Detect and correct document skew using Hough line transform.
    Returns (corrected_image, angle_degrees).
    """
    try:
        import cv2

        gray = np.array(image.convert("L"))
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )
        if lines is None:
            return image, 0.0

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 != x1:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if -45 < angle < 45:
                    angles.append(angle)

        if not angles:
            return image, 0.0

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return image, 0.0  # negligible skew

        # Rotate to correct
        corrected = image.rotate(-median_angle, expand=True, fillcolor=(255, 255, 255))
        logger.debug("Deskewed by %.2f°", median_angle)
        return corrected, round(median_angle, 2)

    except Exception as exc:
        logger.warning("Deskew failed: %s", exc)
        return image, 0.0


def _denoise(image: Image.Image) -> Image.Image:
    """Apply fast non-local means denoising."""
    try:
        import cv2

        img_array = np.array(image.convert("RGB"))
        denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)
        return Image.fromarray(denoised)
    except Exception as exc:
        logger.warning("Denoise failed: %s", exc)
        return image


def _enhance_contrast(image: Image.Image) -> Image.Image:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalisation) per channel."""
    try:
        import cv2

        img_array = np.array(image.convert("RGB"))
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_rgb = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
        return Image.fromarray(enhanced_rgb)
    except Exception as exc:
        logger.warning("Contrast enhancement failed: %s", exc)
        return image
