"""
config/settings.py
Central configuration — all paths, thresholds, and constants live here.
"""
import os
from pathlib import Path

# ── Project Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = BASE_DIR / "core"
MODELS_DIR = BASE_DIR / "models"
CONFIG_DIR = BASE_DIR / "config"
RULES_DIR = CORE_DIR / "rules" / "rule_definitions"
SCORE_CONFIG_PATH = CORE_DIR / "scoring" / "score_config.yaml"
OCR_CACHE_DIR = BASE_DIR / ".ocr_cache"
LOG_DIR = BASE_DIR / "logs"

# Create necessary dirs at import time
OCR_CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── OCR Settings ─────────────────────────────────────────────────────────────
OCR_LANGUAGES = ["en","hi"]
OCR_GPU = False
MAX_OCR_DIMENSION = 2048
OCR_CACHE_TTL = 3600  # seconds

# ── Preprocessing ─────────────────────────────────────────────────────────────
MAX_IMAGE_DIMENSION = 2048
ELA_COMPARISON_QUALITY = 90
ELA_MAX_DIMENSION = 512

# ── Classification ────────────────────────────────────────────────────────────
MIN_CLASSIFICATION_SCORE = 30
HIGH_CONFIDENCE_THRESHOLD = 0.60
MEDIUM_CONFIDENCE_THRESHOLD = 0.35
FUZZY_MATCH_THRESHOLD = 85  # rapidfuzz uses 0–100 scale

# ── Scoring / Verdicts ────────────────────────────────────────────────────────
SCORE_GENUINE_MAX = 25
SCORE_REVIEW_MAX = 55
# Above 55 → SUSPICIOUS

# ── Layout Validation ────────────────────────────────────────────────────────
LAYOUT_POSITION_TOLERANCE = 0.15  # 15% shift before flagging

# ── Font Analysis ─────────────────────────────────────────────────────────────
FONT_SIZE_DEVIATION_THRESHOLD = 0.30  # 30% from line median

# ── Image Forensics ───────────────────────────────────────────────────────────
ELA_STD_MULTIPLIER = 2.5
COPY_MOVE_MIN_MATCHES = 3
NOISE_QUADRANT_THRESHOLD = 2.0  # std dev ratio

# ── App ───────────────────────────────────────────────────────────────────────
APP_TITLE = "DocGuard — Explainable Forgery Detector"
APP_ICON = "🔍"
MAX_UPLOAD_SIZE_MB = 20
