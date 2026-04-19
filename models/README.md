# models/

This directory is a placeholder for serialised ML model artefacts.

## MVP status
The current implementation is **rule-based only** — no ML models are required.

## Future ML integration points

### LayoutLM (document understanding)
```python
# Drop-in replacement for keyword classifier
# OCRResult already stores bboxes in LayoutLM-compatible format
from transformers import LayoutLMForSequenceClassification
model = LayoutLMForSequenceClassification.from_pretrained("microsoft/layoutlm-base-uncased")
```

### CRAFT (text detection)
- Better word-level bounding boxes for low-quality scans
- Saves to: `models/craft_mlt_25k.pth`

### YOLOv8 (region detection)
- Trained on document region labels (photo, QR, logo, signature)
- More robust than template-matching for layout validation
- Saves to: `models/doc_regions_yolov8n.pt`

### Template images
```
models/templates/
    aadhaar_v1_front.png
    aadhaar_v2_front.png
    pan_v1.png
```
Used for ORB feature matching to detect structural deviations.

## Adding a model
1. Save the model file here
2. Update the relevant subsystem class to load it (with `ML_MODEL_AVAILABLE` flag)
3. The `TextValidator.validate()` already has the extension point:
   ```python
   if ML_MODEL_AVAILABLE:
       return self.ml_validator.predict(ocr)
   return self.rule_validator.validate(ocr, doc_type)
   ```
