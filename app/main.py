"""
app/main.py
DocGuard — Explainable Document Forgery Detector
Streamlit entry point.
"""
import sys
import os
import logging
import logging.config
import time
from pathlib import Path

import yaml
import streamlit as st
from PIL import Image

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Logging setup ─────────────────────────────────────────────────────────────
log_config_path = ROOT / "config" / "logging.yaml"
if log_config_path.exists():
    with open(log_config_path) as f:
        logging.config.dictConfig(yaml.safe_load(f))

logger = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocGuard — Forgery Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .verdict-box {
        border-radius: 12px;
        padding: 20px 28px;
        margin: 12px 0;
        text-align: center;
    }
    .genuine-box   { background: #d5f5e3; border: 2px solid #2ecc71; }
    .review-box    { background: #fef9e7; border: 2px solid #f39c12; }
    .suspicious-box{ background: #fadbd8; border: 2px solid #e74c3c; }
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .subsystem-bar {
        height: 8px;
        border-radius: 4px;
        background: linear-gradient(90deg, #e74c3c, #f39c12);
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 DocGuard")
    st.markdown("**Explainable Document Forgery Detection**")
    st.divider()
    st.markdown("**Supported Documents**")
    st.markdown("- 🪪 Aadhaar Card\n- 💳 PAN Card\n- 📜 SSLC Certificate\n- 🗳️ Voter ID\n- 🚗 Driving Licence")
    st.divider()
    st.markdown("**Detection Methods**")
    st.markdown("- Pattern & checksum validation\n- Layout template comparison\n- Font consistency analysis\n- Error Level Analysis (ELA)\n- Copy-move detection\n- Noise inconsistency analysis")
    st.divider()
    st.caption("⚠️ For research/demo purposes. Not a legal determination.")


# ── Main content ──────────────────────────────────────────────────────────────
st.title("🔍 DocGuard — Document Forgery Detector")
st.markdown("Upload a document to analyse it for signs of forgery. "
            "Results include an explainable risk score with evidence.")

uploaded_file = st.file_uploader(
    "Upload document (PDF, JPG, PNG, WEBP)",
    type=["pdf", "jpg", "jpeg", "png", "webp"],
    help="Max 20 MB. Only the first page of PDFs is analysed.",
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    # Show original image preview
    try:
        from core.ingestion import load_document
        import io
        original_image, _ = load_document(io.BytesIO(file_bytes))
    except Exception as exc:
        st.error(f"Could not read file: {exc}")
        st.stop()

    col_img, col_info = st.columns([1, 1])
    with col_img:
        st.image(original_image, caption="Uploaded document", use_container_width=True)
    with col_info:
        st.markdown("### Document Details")
        st.markdown(f"**Filename:** `{uploaded_file.name}`")
        st.markdown(f"**Size:** {len(file_bytes) / 1024:.1f} KB")
        st.markdown(f"**Dimensions:** {original_image.size[0]} × {original_image.size[1]} px")

    st.divider()

    # ── Analysis button ───────────────────────────────────────────────────────
    if st.button("🔎 Analyse Document", type="primary", use_container_width=True):
        with st.spinner("Running analysis pipeline…"):
            progress = st.progress(0, text="Ingesting document…")
            t0 = time.time()

            try:
                import io
                from core import analyze_document

                progress.progress(15, text="Preprocessing image…")
                report = analyze_document(io.BytesIO(file_bytes))
                elapsed = time.time() - t0
                progress.progress(100, text="Done!")
                time.sleep(0.3)
                progress.empty()

            except Exception as exc:
                progress.empty()
                st.error(f"Analysis failed: {exc}")
                logger.exception("Analysis failed")
                st.stop()

        # ── Results ───────────────────────────────────────────────────────────
        st.success(f"✅ Analysis complete in {elapsed:.1f}s")

        # Verdict banner
        verdict = report.verdict
        score = report.confidence_score
        color = report.verdict_color
        css_class = {
            "GENUINE": "genuine-box",
            "NEEDS REVIEW": "review-box",
            "SUSPICIOUS": "suspicious-box",
        }.get(verdict, "review-box")

        verdict_icon = {"GENUINE": "✅", "NEEDS REVIEW": "⚠️", "SUSPICIOUS": "🚨"}.get(verdict, "❓")

        st.markdown(f"""
        <div class="verdict-box {css_class}">
            <h1 style="color:{color}; margin:0">{verdict_icon} {verdict}</h1>
            <h2 style="color:{color}; margin:4px 0">Risk Score: {score:.0f} / 100</h2>
            <p style="margin:0; color:#555">
                Document type: <strong>{report.doc_type.upper()}</strong>
                (classification confidence: {report.doc_type_confidence*100:.0f}%)
            </p>
        </div>
        """, unsafe_allow_html=True)

        # ── Two-column layout: image panel + evidence ─────────────────────────
        left_col, right_col = st.columns([1.1, 0.9])

        with left_col:
            st.markdown("### 🖼️ Image Analysis")
            from app.components.annotated_image import render_image_panel
            render_image_panel(original_image, report)

        with right_col:
            st.markdown("### 📊 Risk Score")
            from app.components.score_gauge import render_score_gauge
            render_score_gauge(score, verdict, color)

            # Subsystem breakdown
            if report.subsystem_scores:
                st.markdown("**Subsystem Contributions**")
                max_sub = max(report.subsystem_scores.values()) or 1
                labels = {"text": "📝 Text", "layout": "📐 Layout",
                          "font": "🔤 Font", "image": "🖼️ Image"}
                for sub, val in sorted(report.subsystem_scores.items(),
                                       key=lambda x: -x[1]):
                    label = labels.get(sub, sub.title())
                    pct = int((val / max_sub) * 100)
                    st.markdown(f"{label}: `{val:.0f}`")
                    st.progress(pct / 100)

        # ── Evidence table ────────────────────────────────────────────────────
        st.markdown("### 🔎 Evidence & Explanations")
        from app.components.evidence_table import render_evidence_table
        render_evidence_table(report)

        # ── Preprocessing metadata ────────────────────────────────────────────
        with st.expander("⚙️ Preprocessing & Pipeline Details"):
            meta = report.preprocessing_meta
            cols = st.columns(4)
            cols[0].metric("Skew Angle", f"{meta.get('skew_angle', 0):.1f}°")
            cols[1].metric("Was Resized", "Yes" if meta.get("was_resized") else "No")
            cols[2].metric("Was Enhanced", "Yes" if meta.get("was_enhanced") else "No")
            cols[3].metric("Format", meta.get("format", "?"))

            if report.classification_signals:
                st.markdown("**Classification signals fired:**")
                st.code("\n".join(report.classification_signals[:10]))

        # ── JSON export ───────────────────────────────────────────────────────
        with st.expander("📥 Export Report (JSON)"):
            import json
            export = {
                "verdict": report.verdict,
                "score": report.confidence_score,
                "doc_type": report.doc_type,
                "doc_type_confidence": report.doc_type_confidence,
                "reasons": [
                    {
                        "short": r.short,
                        "detail": r.detail,
                        "severity": r.severity,
                        "category": r.category,
                        "signal_type": r.signal_type,
                        "subsystem": r.subsystem,
                    }
                    for r in report.reasons
                ],
                "subsystem_scores": report.subsystem_scores,
                "preprocessing": {
                    k: v for k, v in report.preprocessing_meta.items()
                    if isinstance(v, (str, int, float, bool))
                },
            }
            json_str = json.dumps(export, indent=2)
            st.code(json_str, language="json")
            st.download_button(
                "⬇️ Download JSON Report",
                data=json_str,
                file_name=f"docguard_report_{uploaded_file.name}.json",
                mime="application/json",
            )

else:
    # Landing state
    st.markdown("""
    ---
    ### How it works

    1. **Upload** a document image or PDF
    2. **Preprocessing** — deskew, denoise, contrast enhancement
    3. **OCR** — extract text with bounding boxes (EasyOCR + Tesseract fallback)
    4. **Classification** — identify document type via weighted keyword scoring
    5. **4-Subsystem Forgery Detection:**
       - 📝 **Text** — pattern matching, checksums, logical consistency
       - 📐 **Layout** — region detection vs known templates
       - 🔤 **Font** — size and alignment anomalies
       - 🖼️ **Image** — ELA, copy-move, noise inconsistency
    6. **Scoring** — sigmoid-normalised risk score 0–100
    7. **Explainability** — every flag has a human-readable reason

    Upload a document above to get started.
    """)
