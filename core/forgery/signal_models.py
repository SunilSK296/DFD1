"""
core/forgery/signal_models.py
Shared data model for all forgery subsystems.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class ForgerySignal:
    """A single evidence item from a forgery detection subsystem."""
    subsystem: str                          # "text" | "layout" | "font" | "image"
    signal_type: str                        # key into SIGNAL_TO_REASON
    severity: str                           # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    weight: float                           # contribution to risk score
    evidence: str                           # human-readable description
    confidence: float = 1.0                 # 0.0 – 1.0
    location: Optional[Tuple] = None        # bbox (x1,y1,x2,y2) if spatial
    value: Optional[str] = None             # the bad value detected (e.g. wrong PAN)
    expected: Optional[str] = None          # what was expected

    @property
    def effective_weight(self) -> float:
        return self.weight * self.confidence
