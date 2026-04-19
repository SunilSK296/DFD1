#!/usr/bin/env python3
"""
scripts/test_single_doc.py
CLI tool: run the full pipeline on a single document and print results.

Usage:
    python scripts/test_single_doc.py path/to/document.jpg
    python scripts/test_single_doc.py path/to/document.pdf --verbose
    python scripts/test_single_doc.py path/to/doc.png --no-cache
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import analyze_document


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


SEVERITY_COLORS = {
    "CRITICAL": "\033[91m",   # bright red
    "HIGH":     "\033[93m",   # yellow
    "MEDIUM":   "\033[94m",   # blue
    "LOW":      "\033[96m",   # cyan
}
RESET = "\033[0m"
BOLD  = "\033[1m"


def print_report(report):
    verdict_color = {
        "GENUINE":      "\033[92m",   # green
        "NEEDS REVIEW": "\033[93m",   # yellow
        "SUSPICIOUS":   "\033[91m",   # red
    }.get(report.verdict, "\033[0m")

    print()
    print("=" * 60)
    print(f"{BOLD}DocGuard Analysis Report{RESET}")
    print("=" * 60)
    print(f"  Document Type : {BOLD}{report.doc_type.upper()}{RESET} "
          f"(confidence: {report.doc_type_confidence*100:.0f}%)")
    print(f"  Risk Score    : {BOLD}{report.confidence_score:.1f} / 100{RESET}")
    print(f"  Verdict       : {verdict_color}{BOLD}{report.verdict}{RESET}")
    print()

    if report.reasons:
        print(f"{BOLD}Evidence ({len(report.reasons)} indicator(s)):{RESET}")
        print("-" * 60)
        for i, reason in enumerate(report.reasons, 1):
            sev_color = SEVERITY_COLORS.get(reason.severity, "")
            print(f"  {i:2d}. [{sev_color}{reason.severity:8s}{RESET}] {BOLD}{reason.short}{RESET}")
            print(f"       {reason.detail}")
            print()
    else:
        print(f"\033[92m  ✓ No forgery indicators detected.{RESET}\n")

    if report.subsystem_scores:
        print(f"{BOLD}Subsystem Scores:{RESET}")
        for sub, val in sorted(report.subsystem_scores.items(), key=lambda x: -x[1]):
            bar_len = int(val / 5)
            bar = "█" * min(bar_len, 20)
            print(f"  {sub:10s} {val:6.1f}  {bar}")
        print()

    meta = report.preprocessing_meta
    print(f"{BOLD}Pipeline Details:{RESET}")
    print(f"  Skew corrected : {meta.get('skew_angle', 0):.1f}°")
    print(f"  Image resized  : {meta.get('was_resized', False)}")
    print(f"  Enhanced       : {meta.get('was_enhanced', False)}")
    print(f"  Source format  : {meta.get('format', 'unknown')}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="DocGuard: Analyse a document for forgery indicators."
    )
    parser.add_argument("document", help="Path to document (PDF/JPG/PNG/WEBP)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable DEBUG logging")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable OCR disk cache")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON report instead of formatted text")
    args = parser.parse_args()

    setup_logging(args.verbose)

    doc_path = Path(args.document)
    if not doc_path.exists():
        print(f"\033[91mError: File not found: {doc_path}{RESET}", file=sys.stderr)
        sys.exit(1)

    print(f"Analysing: {doc_path.name} …")
    t0 = time.time()

    try:
        report = analyze_document(doc_path, use_ocr_cache=not args.no_cache)
    except Exception as exc:
        print(f"\033[91mAnalysis failed: {exc}{RESET}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)

    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.2f}s")

    if args.json:
        output = {
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
            "elapsed_seconds": round(elapsed, 2),
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
