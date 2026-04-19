"""
app/components/evidence_table.py
Renders the grouped evidence table in Streamlit.
"""
import streamlit as st
from core.explainability.reason_templates import Report

SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🔵",
}

CATEGORY_ICONS = {
    "Format Issues":          "📋",
    "Logical Inconsistencies": "🔢",
    "Layout Issues":           "📐",
    "Visual Anomalies":        "🖼️",
    "Other":                   "❓",
}


def render_evidence_table(report: Report):
    """Display grouped reasons as expandable sections."""
    if not report.reasons:
        st.success("✅ No forgery indicators detected.")
        return

    st.markdown(f"**{len(report.reasons)} indicator(s) found across "
                f"{len(report.grouped_reasons)} category(ies)**")

    for category, reasons in report.grouped_reasons.items():
        icon = CATEGORY_ICONS.get(category, "❓")
        with st.expander(f"{icon} {category} ({len(reasons)})", expanded=True):
            for reason in reasons:
                sev_emoji = SEVERITY_EMOJI.get(reason.severity, "⚪")
                st.markdown(
                    f"{sev_emoji} **{reason.short}**  \n"
                    f"<small style='color:#666'>{reason.detail}</small>",
                    unsafe_allow_html=True,
                )
                st.divider()
