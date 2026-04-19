"""
core/explainability/explainer.py
Maps ForgerySignal list → human-readable Report.
The explainability IS the product — invest here.
"""
import logging
from typing import List, Dict

from core.forgery.signal_models import ForgerySignal
from core.scoring.scorer import compute_score, score_to_verdict, get_subsystem_breakdown
from core.explainability.reason_templates import (
    SIGNAL_TO_REASON,
    CATEGORY_ORDER,
    Reason,
    Report,
)

logger = logging.getLogger(__name__)


class Explainer:
    """Transforms raw signals into a structured, human-readable Report."""

    def generate_report(
        self,
        signals: List[ForgerySignal],
        doc_type: str,
        doc_type_confidence: float,
        preprocessing_meta: dict = None,
        classification_signals: list = None,
    ) -> Report:
        score = compute_score(signals)
        verdict, color = score_to_verdict(score)
        subsystem_scores = get_subsystem_breakdown(signals)

        reasons = self._build_reasons(signals, doc_type)
        grouped = self._group_by_category(reasons)

        # Collect ELA data if image forensics ran
        ela_map = None
        ela_regions = []
        for s in signals:
            if s.signal_type in ("ela_high_anomaly", "ela_medium_anomaly"):
                # The ImageForensics instance stores these; we pass them through signal metadata
                break

        report = Report(
            verdict=verdict,
            verdict_color=color,
            confidence_score=score,
            doc_type=doc_type,
            doc_type_confidence=doc_type_confidence,
            reasons=reasons,
            grouped_reasons=grouped,
            top_reason=reasons[0] if reasons else None,
            subsystem_scores=subsystem_scores,
            preprocessing_meta=preprocessing_meta or {},
            classification_signals=classification_signals or [],
        )

        logger.info(
            "Report: verdict=%s, score=%.1f, reasons=%d, doc_type=%s",
            verdict, score, len(reasons), doc_type,
        )
        return report

    # ── Private helpers ──────────────────────────────────────────────────

    def _build_reasons(
        self, signals: List[ForgerySignal], doc_type: str
    ) -> List[Reason]:
        """Convert signals → Reason objects, sorted by descending weight."""
        reasons = []
        seen_types = set()

        for signal in sorted(signals, key=lambda s: -s.effective_weight):
            if signal.signal_type in seen_types:
                continue  # deduplicate same signal type
            seen_types.add(signal.signal_type)

            template = SIGNAL_TO_REASON.get(signal.signal_type)
            if template is None:
                # Generic fallback
                reasons.append(Reason(
                    short=signal.evidence[:80],
                    detail=signal.evidence,
                    severity=signal.severity,
                    category=self._subsystem_to_category(signal.subsystem),
                    signal_type=signal.signal_type,
                    subsystem=signal.subsystem,
                    location=signal.location,
                ))
                continue

            detail = template["detail"].format(
                value=signal.value or "N/A",
                expected=signal.expected or "N/A",
                delta=abs(int(signal.value or 0) - int(signal.expected or 0))
                       if (signal.value and signal.expected and
                           signal.value.isdigit() and signal.expected.isdigit())
                       else "unknown",
                doc_type=doc_type.upper(),
                region=str(signal.location or "N/A"),
            )

            reasons.append(Reason(
                short=template["short"].format(value=signal.value or ""),
                detail=detail,
                severity=template.get("severity", signal.severity),
                category=template.get("category", "Other"),
                signal_type=signal.signal_type,
                subsystem=signal.subsystem,
                location=signal.location,
            ))

        return reasons

    def _group_by_category(
        self, reasons: List[Reason]
    ) -> Dict[str, List[Reason]]:
        grouped: Dict[str, List[Reason]] = {}
        for reason in reasons:
            grouped.setdefault(reason.category, []).append(reason)
        # Return ordered by CATEGORY_ORDER
        return {
            cat: grouped[cat]
            for cat in CATEGORY_ORDER
            if cat in grouped
        }

    @staticmethod
    def _subsystem_to_category(subsystem: str) -> str:
        mapping = {
            "text": "Format Issues",
            "layout": "Layout Issues",
            "font": "Visual Anomalies",
            "image": "Visual Anomalies",
        }
        return mapping.get(subsystem, "Other")
