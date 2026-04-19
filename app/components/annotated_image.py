"""
app/components/annotated_image.py
Renders the original + annotated + ELA image trio in Streamlit.
"""
import streamlit as st
from PIL import Image
from core.explainability.reason_templates import Report


def render_image_panel(original_image: Image.Image, report: Report):
    """Display image analysis panel: original, annotated, ELA side-by-side."""
    tabs = ["📄 Original", "🔍 Annotated", "🌡️ ELA Analysis", "🔥 Heatmap"]
    tab_objs = st.tabs(tabs)

    with tab_objs[0]:
        st.image(original_image, caption="Original Document", use_container_width=True)

    with tab_objs[1]:
        if hasattr(report, "annotated_image") and report.annotated_image is not None:
            st.image(
                report.annotated_image,
                caption="Annotated — bounding boxes show flagged regions",
                use_container_width=True,
            )
        else:
            st.info("No spatial signals to annotate.")

    with tab_objs[2]:
        if hasattr(report, "ela_image") and report.ela_image is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.image(original_image, caption="Original", use_container_width=True)
            with col2:
                st.image(
                    report.ela_image,
                    caption="ELA Map (bright = potentially edited)",
                    use_container_width=True,
                )
            st.caption(
                "Error Level Analysis: brighter regions indicate areas with different "
                "JPEG compression levels, which may suggest digital editing."
            )
        else:
            st.info("ELA analysis not available for this document.")

    with tab_objs[3]:
        if hasattr(report, "heatmap_image") and report.heatmap_image is not None:
            st.image(
                report.heatmap_image,
                caption="Risk Heatmap — red overlay shows flagged regions",
                use_container_width=True,
            )
        else:
            st.info("No spatial signals to display on heatmap.")
