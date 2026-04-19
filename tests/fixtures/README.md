# tests/fixtures/

Place test documents here in two subdirectories:

```
tests/fixtures/
    genuine/    ← real, unmodified documents (Aadhaar, PAN, SSLC etc.)
    forged/     ← tampered or fabricated documents
```

The `benchmark.py` script uses this directory structure to measure accuracy.

## How to create forged test documents for development

1. Take a genuine document image
2. Open in any image editor (GIMP, Photoshop, etc.)
3. Make small changes:
   - Alter one digit in the Aadhaar/PAN number
   - Change a mark value in an SSLC certificate
   - Remove the QR code
   - Paste text from another document
4. Save as JPG (this preserves JPEG compression artefacts that ELA detects)

> ⚠️ Only use synthetic/sample documents for testing. Never include real
> personal documents in this directory or commit them to version control.

## Included sample documents

None included by default. Add your own test images here.
