"""
app/components/score_gauge.py
Renders an SVG-based risk score gauge in Streamlit.
"""
import streamlit as st


def render_score_gauge(score: float, verdict: str, color: str):
    """
    Display a semicircular gauge for the risk score.
    score: 0–100
    """
    # Map score to angle: 0 → -180°, 100 → 0° (semicircle)
    angle = -180 + (score / 100) * 180

    # Convert angle to SVG arc endpoint
    import math
    rad = math.radians(angle)
    cx, cy, r = 100, 100, 80
    nx = cx + r * math.cos(rad)
    ny = cy + r * math.sin(rad)

    # Background arc colour
    bg_color = "#ecf0f1"
    needle_color = color

    svg = f"""
    <svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" width="300" height="180">
      <!-- Background semicircle -->
      <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="{bg_color}" stroke-width="16" stroke-linecap="round"/>
      <!-- Score arc (coloured portion) -->
      <path d="M 20 100 A 80 80 0 0 1 {nx:.1f} {ny:.1f}"
            fill="none" stroke="{needle_color}" stroke-width="16" stroke-linecap="round"
            opacity="0.85"/>
      <!-- Centre circle -->
      <circle cx="100" cy="100" r="8" fill="{needle_color}"/>
      <!-- Score text -->
      <text x="100" y="88" text-anchor="middle" font-size="26" font-weight="bold"
            fill="{needle_color}" font-family="sans-serif">{score:.0f}</text>
      <text x="100" y="102" text-anchor="middle" font-size="9"
            fill="#7f8c8d" font-family="sans-serif">RISK SCORE</text>
      <!-- Verdict label -->
      <text x="100" y="118" text-anchor="middle" font-size="11" font-weight="bold"
            fill="{needle_color}" font-family="sans-serif">{verdict}</text>
      <!-- Scale labels -->
      <text x="18"  y="114" font-size="8" fill="#95a5a6" font-family="sans-serif">0</text>
      <text x="174" y="114" font-size="8" fill="#95a5a6" font-family="sans-serif">100</text>
    </svg>
    """
    st.markdown(svg, unsafe_allow_html=True)
