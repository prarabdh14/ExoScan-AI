#!/usr/bin/env python3
"""
Validate benchmark exoplanet targets and generate benchmark_reference.csv.

Queries NASA Exoplanet Archive pscomppars for each of the 12 curated systems
and writes validated ephemerides used to verify BLS period recovery.

Usage:
    PYTHONPATH=src python scripts/build_benchmark_reference.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from exoscan.data.benchmark import save_benchmark_reference
from exoscan.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build validated benchmark reference CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "labels" / "benchmark_reference.csv",
        help="Output CSV path",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_logging(args.log_level)
    logger.info("=== ExoScan-AI: Benchmark Validation ===")

    frame = save_benchmark_reference(args.output)

    print("\nBenchmark Validation Summary")
    print("-" * 72)
    for _, row in frame.iterrows():
        status = row["validation_status"]
        marker = "✓" if status in {"validated", "tic_corrected"} else "✗"
        print(
            f"{marker} {row['planet_name']:16s} TIC {str(row['tic_id']):>10s}  "
            f"P={row['period_days']:.4f} d  "
            f"depth={row['transit_depth_fraction']:.5f}  "
            f"dur={row['duration_hours']:.2f} h  "
            f"[{status}]"
            if pd.notna(row["period_days"])
            else f"{marker} {row['planet_name']:16s} TIC {str(row['tic_id']):>10s}  MISSING"
        )
        if row["validation_notes"]:
            print(f"    notes: {row['validation_notes']}")

    missing = (frame["validation_status"] == "missing").sum()
    corrected = (frame["validation_status"] == "tic_corrected").sum()
    print("-" * 72)
    print(f"Total: {len(frame)} | Validated: {len(frame) - missing} | TIC corrected: {corrected}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
