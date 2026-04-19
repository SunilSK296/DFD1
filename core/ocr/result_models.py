"""
core/ocr/result_models.py
Dataclasses for OCR output — used across the entire pipeline.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class TextBlock:
    """A single detected text region."""
    text: str
    bbox: Tuple[int, int, int, int]   # x1, y1, x2, y2
    confidence: float                  # 0.0 – 1.0
    language: str = "en"
    line_number: int = 0
    font_size_estimate: float = 12.0  # bbox height as proxy

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def center_x(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def center_y(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


@dataclass
class OCRResult:
    """Aggregated OCR output for a document."""
    blocks: List[TextBlock] = field(default_factory=list)
    full_text: str = ""
    languages_detected: List[str] = field(default_factory=list)
    avg_confidence: float = 0.0
    low_confidence_count: int = 0

    def get_text_in_region(self, bbox: Tuple[float, float, float, float],
                            image_size: Tuple[int, int]) -> str:
        """
        Return concatenated text of blocks whose centres fall within a
        normalised bounding box (x1, y1, x2, y2 in 0–1 range).
        """
        w, h = image_size
        x1, y1, x2, y2 = bbox[0]*w, bbox[1]*h, bbox[2]*w, bbox[3]*h
        texts = []
        for block in self.blocks:
            cx, cy = block.center_x, block.center_y
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                texts.append(block.text)
        return " ".join(texts)

    def get_low_confidence_blocks(self, threshold: float = 0.5) -> List[TextBlock]:
        return [b for b in self.blocks if b.confidence < threshold]
