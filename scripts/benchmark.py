#!/usr/bin/env python3
"""
scripts/benchmark.py
Batch accuracy benchmark against a labelled test set.

Directory structure expected:
    tests/fixtures/
        genuine/   ← documents known to be real
        forged/    ← documents known to be tampered

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --fixture-dir path/to/fixtures --threshold 55
"""
import argparse
import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING)  # quiet during benchmark

from core import analyze_document

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def collect_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return [f for f in directory.iterdir() if f.suffix.lower() in IMAGE_EXTS]


def run_benchmark(fixture_dir: Path, suspicious_threshold: float = 55.0):
    genuine_dir = fixture_dir / "genuine"
    forged_dir  = fixture_dir / "forged"

    genuine_files = collect_files(genuine_dir)
    forged_files  = collect_files(forged_dir)

    if not genuine_files and not forged_files:
        print(f"No fixture files found in {fixture_dir}")
        print("Create subdirectories 'genuine/' and 'forged/' with sample documents.")
        return

    results: List[Dict] = []
    errors = 0

    def analyse(path: Path, expected_label: str):
        nonlocal errors
        try:
            t0 = time.time()
            report = analyze_document(path, use_ocr_cache=True)
            elapsed = time.time() - t0
            predicted = "SUSPICIOUS" if report.confidence_score > suspicious_threshold else "GENUINE"
            correct = (
                (expected_label == "GENUINE"    and predicted == "GENUINE") or
                (expected_label == "SUSPICIOUS" and predicted == "SUSPICIOUS")
            )
            results.append({
                "file":          path.name,
                "expected":      expected_label,
                "predicted":     predicted,
                "verdict":       report.verdict,
                "score":         report.confidence_score,
                "doc_type":      report.doc_type,
                "correct":       correct,
                "elapsed":       round(elapsed, 2),
                "top_signal":    report.reasons[0].short if report.reasons else "—",
            })
        except Exception as exc:
            errors += 1
            print(f"  ERROR on {path.name}: {exc}")

    print(f"\nRunning benchmark on {len(genuine_files)} genuine + {len(forged_files)} forged documents…\n")

    for f in genuine_files:
        print(f"  genuine  → {f.name}")
        analyse(f, "GENUINE")

    for f in forged_files:
        print(f"  forged   → {f.name}")
        analyse(f, "SUSPICIOUS")

    # ── Summary ───────────────────────────────────────────────────────────────
    if not results:
        print("No results to summarise.")
        return

    total     = len(results)
    correct   = sum(1 for r in results if r["correct"])
    accuracy  = correct / total * 100

    true_pos  = sum(1 for r in results if r["expected"] == "SUSPICIOUS" and r["correct"])
    false_pos = sum(1 for r in results if r["expected"] == "GENUINE"    and not r["correct"])
    false_neg = sum(1 for r in results if r["expected"] == "SUSPICIOUS" and not r["correct"])

    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
    recall    = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0)

    avg_elapsed = sum(r["elapsed"] for r in results) / total

    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    print(f"  Total documents : {total} ({len(genuine_files)} genuine, {len(forged_files)} forged)")
    print(f"  Correct         : {correct} / {total}")
    print(f"  Accuracy        : {accuracy:.1f}%")
    print(f"  Precision       : {precision:.1%}")
    print(f"  Recall          : {recall:.1%}")
    print(f"  F1 Score        : {f1:.1%}")
    print(f"  Avg time/doc    : {avg_elapsed:.2f}s")
    print(f"  Errors          : {errors}")
    print()

    print("Per-document Results:")
    print(f"  {'File':<30} {'Expected':<12} {'Predicted':<12} {'Score':>6}  {'OK'}")
    print("  " + "-" * 68)
    for r in results:
        ok = "✓" if r["correct"] else "✗"
        print(f"  {r['file']:<30} {r['expected']:<12} {r['predicted']:<12} "
              f"{r['score']:>6.1f}  {ok}")

    print("=" * 70)
    return results


def main():
    parser = argparse.ArgumentParser(description="DocGuard batch benchmark")
    parser.add_argument(
        "--fixture-dir", default=str(ROOT / "tests" / "fixtures"),
        help="Path to fixtures directory (default: tests/fixtures/)"
    )
    parser.add_argument(
        "--threshold", type=float, default=55.0,
        help="Score threshold above which a document is flagged SUSPICIOUS (default: 55)"
    )
    args = parser.parse_args()

    run_benchmark(Path(args.fixture_dir), args.threshold)


if __name__ == "__main__":
    main()
