"""
core/ingestion.py
Accept file, detect format, convert to PIL Image + metadata dict.
This is the ONLY place in the codebase that knows about file formats.
"""
import io
import logging
from pathlib import Path
from typing import Tuple, Dict, Any

from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS | {".pdf"}


def load_document(file_source) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Load a document from a file path or bytes-like object.

    Returns:
        (PIL.Image, metadata_dict)

    Metadata keys: format, original_size, dpi, page_count, source_path
    """
    if isinstance(file_source, (str, Path)):
        path = Path(file_source)
        suffix = path.suffix.lower()
        with open(path, "rb") as fh:
            data = fh.read()
        source_name = str(path)
    elif hasattr(file_source, "read"):
        # Streamlit UploadedFile or file-like
        data = file_source.read()
        source_name = getattr(file_source, "name", "upload")
        suffix = Path(source_name).suffix.lower()
    elif isinstance(file_source, bytes):
        data = file_source
        source_name = "bytes_input"
        suffix = _detect_suffix_from_bytes(data)
    else:
        raise ValueError(f"Unsupported source type: {type(file_source)}")

    if suffix == ".pdf":
        return _load_pdf(data, source_name)
    elif suffix in SUPPORTED_IMAGE_FORMATS:
        return _load_image(data, source_name)
    else:
        # Try image anyway
        logger.warning("Unknown extension '%s', attempting image load.", suffix)
        return _load_image(data, source_name)


def _load_pdf(data: bytes, source_name: str) -> Tuple[Image.Image, Dict[str, Any]]:
    """Render first page of PDF at 200 DPI → PIL Image."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber is required for PDF support. Run: pip install pdfplumber")

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        page = pdf.pages[0]
        # Render to PIL image at 200 DPI
        pil_image = page.to_image(resolution=200).original
        w, h = pil_image.size

    metadata = {
        "format": "PDF",
        "original_size": (w, h),
        "dpi": 200,
        "page_count": page_count,
        "source_path": source_name,
    }
    logger.info("Loaded PDF '%s': %d pages, rendered page 1 at %s", source_name, page_count, (w, h))
    return pil_image.convert("RGB"), metadata


def _load_image(data: bytes, source_name: str) -> Tuple[Image.Image, Dict[str, Any]]:
    """Load image bytes → PIL Image."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()  # force decode
    except Exception as exc:
        raise ValueError(f"Cannot decode image from '{source_name}': {exc}") from exc

    fmt = image.format or "UNKNOWN"
    dpi = image.info.get("dpi", (72, 72))
    if isinstance(dpi, (int, float)):
        dpi = (dpi, dpi)

    metadata = {
        "format": fmt,
        "original_size": image.size,
        "dpi": dpi[0],
        "page_count": 1,
        "source_path": source_name,
    }
    logger.info("Loaded image '%s': format=%s, size=%s", source_name, fmt, image.size)
    return image.convert("RGB"), metadata


def _detect_suffix_from_bytes(data: bytes) -> str:
    """Heuristic format detection from magic bytes."""
    if data[:4] == b"%PDF":
        return ".pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] in (b"\xff\xd8", b"\xff\xe0", b"\xff\xe1"):
        return ".jpg"
    return ".jpg"  # fallback
