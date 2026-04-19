# DocGuard — Explainable Document Forgery Detector

A production-quality pipeline for detecting forgery in Indian identity documents
(Aadhaar, PAN, SSLC certificates, Voter ID, Driving Licence) with full explainability.

## Key Features

- **4-subsystem forgery detection**: text patterns, layout templates, font analysis, image forensics
- **Explainable results**: every flag has a human-readable reason — no black boxes
- **Risk score 0–100**: sigmoid-normalised, with three verdict tiers
- **Multilingual OCR**: English, Hindi (Devanagari), Kannada, Telugu
- **Aadhaar Verhoeff checksum**: mathematical validation of genuine Aadhaar numbers
- **ELA forensics**: Error Level Analysis detects digitally edited regions
- **Streamlit dashboard**: annotated image, ELA side-by-side, evidence table, JSON export
- **Zero ML required**: all rule-based — fast, explainable, and tunable without retraining
- **Extensible**: YAML rules, swap-in ML models, add doc types with one file

---

## Quick Start

### 1. Install dependencies

```bash
# System packages (Ubuntu/Debian)
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng libzbar0 libmagic1 poppler-utils

# Python packages
pip install -r requirements.txt
```

### 2. Run the Streamlit app

```bash
streamlit run app/main.py
```

Open `http://localhost:8501` in your browser.

### 3. Run the CLI analyser

```bash
python scripts/test_single_doc.py path/to/document.jpg
python scripts/test_single_doc.py path/to/document.pdf --verbose
python scripts/test_single_doc.py path/to/document.jpg --json   # JSON output
```

### 4. Run tests

```bash
pytest tests/ -v
```

### 5. Docker

```bash
docker build -t docguard .
docker run -p 8501:8501 docguard
```

---

## Architecture

```
[Document Input]
      │
      ▼
[Ingestion]          PDF/Image normalisation, format detection
      │
      ▼
[Preprocessing]      Deskew, denoise, CLAHE contrast, resize
      │
      ▼
[OCR]                EasyOCR (multilingual) + Tesseract fallback + disk cache
      │
      ▼
[Classification]     Keyword scoring + regex patterns → doc_type
      │
      ▼
[Forgery Detection]  4 parallel subsystems:
      │                ├── Text Validator    (patterns, checksums, logic)
      │                ├── Layout Validator  (template region matching)
      │                ├── Font Analyzer     (size/alignment anomalies)
      │                └── Image Forensics   (ELA, copy-move, noise)
      ▼
[Scoring]            Weighted aggregation → sigmoid normalised [0–100]
      │
      ▼
[Explainability]     Signals → human-readable reasons + annotated images
      │
      ▼
[Streamlit UI]       Dashboard: gauge, evidence table, ELA view, JSON export
```

---

## Project Structure

```
doc_forgery_detector/
├── app/                        # Streamlit UI (zero business logic)
│   ├── main.py                 # Entry point
│   └── components/             # Gauge, evidence table, image panel
│
├── core/                       # All business logic
│   ├── ingestion.py            # PDF/image loading
│   ├── preprocessor.py         # OpenCV pipeline
│   ├── ocr/                    # OCR engine + models
│   ├── classifier/             # Keyword scoring classifier
│   ├── forgery/                # 4 detection subsystems + orchestrator
│   ├── rules/                  # YAML rule definitions per doc type
│   ├── scoring/                # Score aggregation + thresholds
│   └── explainability/         # Reason templates + report builder
│
├── config/                     # Settings, logging config
├── models/                     # ML model artefacts (future use)
├── tests/                      # Unit tests + benchmark
├── scripts/                    # CLI tools
├── requirements.txt
└── Dockerfile
```

---

## Supported Document Types

| Document       | Checks                                                    |
|----------------|-----------------------------------------------------------|
| Aadhaar Card   | 12-digit format, Verhoeff checksum, QR presence, layout  |
| PAN Card       | AAAAA9999A format, category code, photo region           |
| SSLC Certificate | Register number, marks sum validation, header layout  |
| Voter ID       | EPIC number format                                        |
| Driving Licence | DL number format                                         |

---

## Detection Methods

### Text Validation
- Regex pattern matching (with OCR error tolerance)
- **Aadhaar Verhoeff checksum** — mathematical proof of validity
- PAN entity category code validation
- SSLC marks sum consistency check
- Required field presence detection

### Layout Validation
- QR code detection and position verification (pyzbar)
- Photo region content check (blank region detection)
- Text alignment consistency across rows

### Font Analysis
- Font size deviation from line median (>30% = suspicious)
- OCR confidence heatmap — low-confidence spatial clusters

### Image Forensics
- **Error Level Analysis (ELA)** — JPEG compression inconsistencies
- Copy-move detection — duplicate image patches
- Noise level inconsistency across quadrants

---

## Scoring

```
raw_score = Σ weight(signal) × confidence(signal)
risk_score = 100 × (1 − e^(−raw / 80))

0–25    → GENUINE
26–55   → NEEDS REVIEW
56–100  → SUSPICIOUS
```

All weights live in `core/scoring/score_config.yaml` — tune without code changes.

---

## Configuration

| File | Purpose |
|------|---------|
| `config/settings.py` | All paths, thresholds, constants |
| `core/scoring/score_config.yaml` | Signal weights and verdict thresholds |
| `core/classifier/keyword_config.py` | Per-doc-type keyword weights |
| `core/rules/rule_definitions/*.yaml` | Document-specific validation rules |

---

## Adding a New Document Type

1. Add keyword signals to `core/classifier/keyword_config.py`
2. Create `core/rules/rule_definitions/your_doc.yaml`
3. (Optional) Add layout template to `core/forgery/layout_validator.py`
4. Add score weights to `core/scoring/score_config.yaml`

No other code changes required.

---

## Engineering Notes

- `core/` has **zero UI imports** — fully testable without Streamlit
- OCR results are **disk-cached** by image MD5 — repeated analysis is instant
- Each forgery subsystem runs in its own thread; one crash never kills the pipeline
- ELA thresholds are **self-calibrating** against the document's own baseline
- Binary verdict is avoided — a score of 67/100 honestly communicates uncertainty

---

## Limitations

- ELA produces false positives on multiply-scanned documents (mitigated by self-calibration)
- Layout validation degrades on heavily cropped / phone-photographed documents
- Font analysis may false-positive on multilingual documents (Devanagari + Latin)
- Marks sum validation requires legible numbers — OCR noise can affect accuracy
- Not a legal determination; designed for screening and triage

---

## License

For educational and research use. See LICENSE for details.
