#!/usr/bin/env python3
"""
Build training_labels.csv and benchmark_targets.csv from external catalogs.

Steps:
  1. Load catalog CSVs from data/external/
  2. Deduplicate by TIC ID (priority: transit > binary > blend > starspot > noise)
  3. Subsample to per-class targets from configs/data.yaml
  4. Write data/labels/training_labels.csv
  5. Write data/labels/benchmark_targets.csv

Usage:
    PYTHONPATH=src python scripts/build_training_labels.py
    PYTHONPATH=src python scripts/build_training_labels.py --include-benchmark-in-training
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from exoscan.config import load_config
from exoscan.data.catalog import (
    build_benchmark_targets,
    build_training_labels,
    deduplicate_candidates,
    load_catalog_frame,
)
from exoscan.utils.logging import setup_logging

CATALOG_FILES = {
    "transit": "nasa_confirmed_planets.csv",
    "binary": "tess_ebs_catalog.csv",
    "blend": "toi_blend_flags.csv",
    "starspot": "rotation_catalog.csv",
    "noise": "quiet_star_sample.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ExoScan-AI training labels")
    parser.add_argument(
        "--external-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "external",
        help="Directory containing downloaded catalog CSVs",
    )
    parser.add_argument(
        "--labels-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "labels",
        help="Output directory for label files",
    )
    parser.add_argument(
        "--include-benchmark-in-training",
        action="store_true",
        help="Do not exclude benchmark TIC IDs from training set",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_logging(args.log_level)
    config = load_config()
    config.ensure_directories(PROJECT_ROOT)

    external_dir = args.external_dir
    labels_dir = args.labels_dir
    labels_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== ExoScan-AI Phase 1: Build Training Labels ===")
    logger.info("Loading catalogs from %s", external_dir)

    catalogs: dict[str, pd.DataFrame] = {}
    for label, filename in CATALOG_FILES.items():
        path = external_dir / filename
        if not path.exists():
            logger.warning("Missing catalog file: %s (run download_catalogs.py first)", path)
            continue
        catalogs[label] = load_catalog_frame(path)
        logger.info("Loaded %s: %s rows", filename, len(catalogs[label]))

    if not catalogs:
        logger.error("No catalog files found. Run scripts/download_catalogs.py first.")
        return 1

    deduped = deduplicate_candidates(catalogs)
    if deduped.empty:
        logger.error("No targets after deduplication.")
        return 1

    class_targets = config.data.get("class_targets", {})
    training = build_training_labels(
        deduped,
        class_targets=class_targets,
        random_seed=config.project.random_seed,
    )

    planet_catalog = catalogs.get("transit")
    benchmark = build_benchmark_targets(planet_catalog)

    if not args.include_benchmark_in_training:
        benchmark_tics = set(benchmark["tic_id"].astype(str))
        before = len(training)
        training = training[~training["tic_id"].isin(benchmark_tics)].reset_index(drop=True)
        removed = before - len(training)
        if removed:
            logger.info("Excluded %s benchmark targets from training set", removed)

    training_path = labels_dir / "training_labels.csv"
    benchmark_path = labels_dir / "benchmark_targets.csv"
    deduped_path = external_dir / "deduplicated_candidates.csv"

    training.to_csv(training_path, index=False)
    benchmark.to_csv(benchmark_path, index=False)
    deduped.to_csv(deduped_path, index=False)

    logger.info("Wrote training labels: %s (%s rows)", training_path, len(training))
    logger.info("Wrote benchmark targets: %s (%s rows)", benchmark_path, len(benchmark))
    logger.info("Wrote deduplicated catalog: %s (%s rows)", deduped_path, len(deduped))

    logger.info("--- Class distribution (training) ---")
    for label, count in training["label"].value_counts().sort_index().items():
        logger.info("  %s: %s", label, count)

    logger.info("=== Label build complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
