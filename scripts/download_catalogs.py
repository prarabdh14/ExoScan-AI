#!/usr/bin/env python3
"""
Download external catalogs for ExoScan-AI Phase 1 dataset acquisition.

Downloads:
  - NASA Exoplanet Archive confirmed TESS planets (transit)
  - TESS Eclipsing Binary catalog via VizieR (binary)
  - TESS rotation catalog (starspot)
  - NASA TOI false positives (blend)
  - TIC field sample (noise)

Usage:
    PYTHONPATH=src python scripts/download_catalogs.py
    PYTHONPATH=src python scripts/download_catalogs.py --skip-noise
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from exoscan.config import load_config
from exoscan.data.catalog import (
    fetch_nasa_confirmed_planets,
    fetch_starspot_candidates,
    fetch_tess_ebs_catalog,
    fetch_toi_false_positives,
    generate_noise_sample,
    save_catalog_frame,
)
from exoscan.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download ExoScan-AI external catalogs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "external",
        help="Directory for catalog CSV files",
    )
    parser.add_argument("--skip-noise", action="store_true", help="Skip noise-class generation")
    parser.add_argument("--noise-count", type=int, default=None, help="Noise class target count")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_logging(args.log_level)
    config = load_config()
    config.ensure_directories(PROJECT_ROOT)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    class_targets = config.data.get("class_targets", {})
    random_seed = config.project.random_seed

    logger.info("=== ExoScan-AI Phase 1: Catalog Download ===")
    logger.info("Output directory: %s", output_dir)

    planets = fetch_nasa_confirmed_planets()
    save_catalog_frame(planets, output_dir / "nasa_confirmed_planets.csv")

    ebs = fetch_tess_ebs_catalog()
    save_catalog_frame(ebs, output_dir / "tess_ebs_catalog.csv")

    starspots = fetch_starspot_candidates(limit=class_targets.get("starspot", 60))
    save_catalog_frame(starspots, output_dir / "rotation_catalog.csv")

    blends = fetch_toi_false_positives(limit=class_targets.get("blend", 40))
    save_catalog_frame(blends, output_dir / "toi_blend_flags.csv")

    if not args.skip_noise:
        reserved = set(planets["tic_id"].astype(str)) | set(ebs["tic_id"].astype(str))
        reserved |= set(starspots["tic_id"].astype(str)) | set(blends["tic_id"].astype(str))
        noise_count = args.noise_count or class_targets.get("noise", 80)
        noise = generate_noise_sample(
            reserved,
            target_count=noise_count,
            random_seed=random_seed,
        )
        save_catalog_frame(noise, output_dir / "quiet_star_sample.csv")
    else:
        logger.info("Skipped noise-class generation (--skip-noise)")

    logger.info("=== Catalog download complete ===")
    logger.info("Next step: PYTHONPATH=src python scripts/build_training_labels.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
