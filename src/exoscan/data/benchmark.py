"""Benchmark reference ephemerides for BLS validation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

from exoscan.data.catalog import BENCHMARK_SYSTEMS, _safe_float, _safe_str, normalize_tic_id
from exoscan.utils.retry import retry_with_backoff

logger = logging.getLogger("exoscan.benchmark")

# NASA pscomppars planet name when it differs from our display label.
ARCHIVE_NAME_OVERRIDES: dict[str, str] = {
    "HD 21749 b": "HD 21749 c",  # Inner transiting planet; archive uses 'c' designation
    "Pi Men c": "pi Men c",  # NASA archive uses lowercase 'pi'
}


@retry_with_backoff(max_attempts=3, initial_delay=3.0, exceptions=(Exception,))
def _query_planet(planet_name: str) -> pd.DataFrame:
    table = NasaExoplanetArchive.query_criteria(
        table="pscomppars",
        select=(
            "pl_name,hostname,tic_id,pl_orbper,pl_orbpererr1,pl_trandep,"
            "pl_trandeperr1,pl_trandur,pl_trandurerr1,disc_facility,disc_refname"
        ),
        where=f"pl_name='{planet_name}'",
    )
    return table.to_pandas()


def _best_archive_row(frame: pd.DataFrame) -> pd.Series | None:
    if frame.empty:
        return None
    scored = frame.copy()
    scored["_score"] = (
        scored["pl_orbper"].notna().astype(int)
        + scored["pl_trandep"].notna().astype(int)
        + scored["pl_trandur"].notna().astype(int)
    )
    return scored.sort_values("_score", ascending=False).iloc[0]


def validate_benchmark_target(system: dict[str, Any]) -> dict[str, Any]:
    """Validate one benchmark system against NASA Exoplanet Archive."""
    display_name = system["display_name"]
    archive_name = ARCHIVE_NAME_OVERRIDES.get(display_name, display_name)
    priority = BENCHMARK_SYSTEMS.index(system) + 1

    row = _best_archive_row(_query_planet(archive_name))
    if row is None:
        return {
            "benchmark_priority": priority,
            "planet_name": display_name,
            "tic_id": system["tic_id"],
            "host_star": system["host_name"],
            "period_days": None,
            "transit_depth_fraction": None,
            "duration_hours": None,
            "source_catalog": "NOT FOUND",
            "validation_status": "missing",
            "validation_notes": f"No pscomppars entry for '{archive_name}'",
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

    tic_id = normalize_tic_id(row["tic_id"])
    period = _safe_float(row["pl_orbper"])
    depth_pct = _safe_float(row["pl_trandep"])
    depth_fraction = depth_pct / 100.0 if depth_pct is not None else None
    duration_hours = _safe_float(row["pl_trandur"])
    host_star = _safe_str(row["hostname"]) or system["host_name"]

    notes: list[str] = []
    validation_status = "validated"
    if tic_id != system["tic_id"]:
        notes.append(f"TIC corrected {system['tic_id']} → {tic_id}")
        validation_status = "tic_corrected"
    if archive_name != display_name:
        notes.append(f"Archive pl_name='{archive_name}' (display: {display_name})")
    if system.get("notes"):
        notes.append(system["notes"])

    return {
        "benchmark_priority": priority,
        "planet_name": display_name,
        "tic_id": tic_id,
        "host_star": host_star,
        "period_days": period,
        "period_err_days": _safe_float(row.get("pl_orbpererr1")),
        "transit_depth_fraction": depth_fraction,
        "transit_depth_pct": depth_pct,
        "duration_hours": duration_hours,
        "duration_days": duration_hours / 24.0 if duration_hours is not None else None,
        "duration_err_hours": _safe_float(row.get("pl_trandurerr1")),
        "source_catalog": "NASA Exoplanet Archive pscomppars",
        "disc_facility": _safe_str(row.get("disc_facility")),
        "validation_status": validation_status,
        "validation_notes": "; ".join(notes),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_benchmark_reference() -> pd.DataFrame:
    """Validate all 12 benchmark targets and return reference dataframe."""
    records: list[dict[str, Any]] = []
    for system in BENCHMARK_SYSTEMS:
        logger.info("Validating %s (TIC %s)...", system["display_name"], system["tic_id"])
        records.append(validate_benchmark_target(system))
    frame = pd.DataFrame(records)
    logger.info(
        "Validated %s/%s benchmarks",
        (frame["validation_status"] != "missing").sum(),
        len(frame),
    )
    return frame


def save_benchmark_reference(output_path: Path) -> pd.DataFrame:
    """Build and save benchmark_reference.csv."""
    frame = build_benchmark_reference()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Saved benchmark reference → %s", output_path)

    # Keep benchmark_targets.csv in sync for dashboard/demo use.
    targets_path = output_path.parent / "benchmark_targets.csv"
    targets = frame[
        [
            "tic_id",
            "planet_name",
            "host_star",
            "period_days",
            "transit_depth_fraction",
            "duration_days",
            "validation_notes",
            "benchmark_priority",
            "source_catalog",
            "validated_at",
        ]
    ].rename(
        columns={
            "planet_name": "display_name",
            "host_star": "host_name",
            "period_days": "period",
            "transit_depth_fraction": "depth",
            "duration_days": "duration",
            "validation_notes": "notes",
        }
    )
    targets.insert(3, "label", "transit")
    targets.to_csv(targets_path, index=False)
    logger.info("Updated benchmark targets → %s", targets_path)
    return frame
