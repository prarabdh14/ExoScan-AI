"""Catalog download and candidate generation for Phase 1."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import astropy.coordinates as coord
import astropy.units as u
import numpy as np
import pandas as pd
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
from astroquery.mast import Catalogs
from astroquery.vizier import Vizier
from tqdm import tqdm

from exoscan.utils.retry import retry_with_backoff

logger = logging.getLogger("exoscan.catalog")

# Well-known TESS exoplanet systems for benchmarking (TIC IDs verified via NASA Archive).
BENCHMARK_SYSTEMS: list[dict[str, Any]] = [
    {
        "tic_id": "25155310",
        "display_name": "TOI-700 b",
        "host_name": "TOI-700",
        "label": "transit",
        "notes": "Earth-sized habitable-zone planet; iconic TESS discovery",
    },
    {
        "tic_id": "441420236",
        "display_name": "LHS 3844 b",
        "host_name": "LHS 3844",
        "label": "transit",
        "notes": "Rocky super-Earth with strong TESS transit",
    },
    {
        "tic_id": "261136679",
        "display_name": "Pi Men c",
        "host_name": "Pi Men",
        "label": "transit",
        "notes": "Warm Jupiter detected by TESS",
    },
    {
        "tic_id": "122641481",
        "display_name": "HD 21749 b",
        "host_name": "HD 21749",
        "label": "transit",
        "notes": "Sub-Neptune with clear TESS transit",
    },
    {
        "tic_id": "349577333",
        "display_name": "GJ 357 b",
        "host_name": "GJ 357",
        "label": "transit",
        "notes": "Nearby transiting super-Earth",
    },
    {
        "tic_id": "307210830",
        "display_name": "WASP-12 b",
        "host_name": "WASP-12",
        "label": "transit",
        "notes": "Ultra-hot Jupiter; deep transit",
    },
    {
        "tic_id": "441462736",
        "display_name": "AU Mic b",
        "host_name": "AU Mic",
        "label": "transit",
        "notes": "Young star with transiting Neptune",
    },
    {
        "tic_id": "229093918",
        "display_name": "L 98-59 b",
        "host_name": "L 98-59",
        "label": "transit",
        "notes": "Multi-planet M-dwarf system",
    },
    {
        "tic_id": "260728333",
        "display_name": "TOI-1338 b",
        "host_name": "TOI-1338",
        "label": "transit",
        "notes": "Circumbinary planet candidate",
    },
    {
        "tic_id": "166620049",
        "display_name": "KELT-9 b",
        "host_name": "KELT-9",
        "label": "transit",
        "notes": "Extremely hot Jupiter",
    },
    {
        "tic_id": "41472818",
        "display_name": "NGTS-2 b",
        "host_name": "NGTS-2",
        "label": "transit",
        "notes": "Hot Jupiter with TESS coverage",
    },
    {
        "tic_id": "39699648",
        "display_name": "HD 77946 b",
        "host_name": "HD 77946",
        "label": "transit",
        "notes": "TESS-discovered warm giant",
    },
]

# Southern ecliptic pole sky patches for sampling quiet field stars.
NOISE_SKY_PATCHES: list[tuple[float, float]] = [
    (180.0, -65.0),
    (210.0, -55.0),
    (150.0, -70.0),
    (90.0, -60.0),
    (240.0, -50.0),
    (120.0, -45.0),
    (200.0, -75.0),
    (170.0, -58.0),
    (195.0, -62.0),
    (165.0, -48.0),
    (225.0, -68.0),
    (135.0, -72.0),
    (105.0, -52.0),
    (255.0, -58.0),
    (75.0, -68.0),
    (285.0, -55.0),
]

LABEL_PRIORITY = {
    "transit": 0,
    "binary": 1,
    "blend": 2,
    "starspot": 3,
    "noise": 4,
}


def _safe_float(value: Any) -> float | None:
    """Convert astropy Table / masked values to float safely."""
    if value is None:
        return None
    if hasattr(value, "mask") and value.mask:
        return None
    if hasattr(value, "value"):
        value = value.value
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str:
    if value is None or (hasattr(value, "mask") and value.mask):
        return ""
    return str(value.value if hasattr(value, "value") else value)


def normalize_tic_id(value: Any) -> str | None:
    """Normalize TIC identifiers to a numeric string without prefixes."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if hasattr(value, "mask") and value.mask:
        return None
    text = _safe_str(value).strip().upper()
    if not text or text in {"NONE", "NULL", "NAN", "--"}:
        return None
    text = text.replace("TIC", "").replace("-", "").strip()
    if not text.isdigit():
        digits = "".join(ch for ch in text if ch.isdigit())
        text = digits
    if not text:
        return None
    return str(int(text))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@retry_with_backoff(max_attempts=3, initial_delay=3.0, exceptions=(Exception,))
def fetch_nasa_confirmed_planets() -> pd.DataFrame:
    """Download TESS-confirmed planets from NASA Exoplanet Archive pscomppars."""
    logger.info("Querying NASA Exoplanet Archive (pscomppars, TESS discoveries)...")
    table = NasaExoplanetArchive.query_criteria(
        table="pscomppars",
        select="pl_name,hostname,disc_facility,pl_orbper,pl_trandep,pl_trandur,tic_id",
        where="disc_facility like '%TESS%'",
    )
    rows: list[dict[str, Any]] = []
    for record in table:
        tic_id = normalize_tic_id(record["tic_id"])
        if tic_id is None:
            continue
        period = _safe_float(record["pl_orbper"])
        depth = _safe_float(record["pl_trandep"])
        duration_hours = _safe_float(record["pl_trandur"])
        duration_days = duration_hours / 24.0 if duration_hours is not None else None
        rows.append(
            {
                "tic_id": tic_id,
                "pl_name": _safe_str(record["pl_name"]),
                "hostname": _safe_str(record["hostname"]),
                "label": "transit",
                "label_source": "nasa_pscomppars",
                "label_confidence": "high",
                "period": period,
                "depth": depth,
                "duration": duration_days,
                "source_catalog": "NASA Exoplanet Archive pscomppars",
                "notes": f"TESS discovery via {_safe_str(record['disc_facility'])}",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame = frame.sort_values(["tic_id", "period"], na_position="last")
    frame = frame.drop_duplicates(subset=["tic_id"], keep="first")
    logger.info("Fetched %s confirmed TESS planet targets", len(frame))
    return frame.reset_index(drop=True)


@retry_with_backoff(max_attempts=3, initial_delay=3.0, exceptions=(Exception,))
def fetch_tess_ebs_catalog() -> pd.DataFrame:
    """Download TESS Eclipsing Binary catalog from VizieR (J/ApJS/258/16)."""
    logger.info("Downloading TESS-EBs catalog from VizieR (J/ApJS/258/16)...")
    vizier = Vizier(columns=["TIC", "Per", "Dp-pf", "Wp-pf", "Morph", "Tmag", "m_TIC"])
    vizier.ROW_LIMIT = -1
    catalog = vizier.get_catalogs("J/ApJS/258/16/tess-ebs")[0]
    rows: list[dict[str, Any]] = []
    for record in catalog:
        if int(_safe_float(record["m_TIC"]) or 0) != 1:
            continue
        tic_id = normalize_tic_id(record["TIC"])
        if tic_id is None:
            continue
        period = _safe_float(record["Per"])
        depth = _safe_float(record["Dp-pf"])
        duration = _safe_float(record["Wp-pf"])
        rows.append(
            {
                "tic_id": tic_id,
                "label": "binary",
                "label_source": "tess_ebs_vizier",
                "label_confidence": "high",
                "period": period,
                "depth": depth,
                "duration": duration,
                "morphology": _safe_float(record["Morph"]),
                "tmag": _safe_float(record["Tmag"]),
                "source_catalog": "TESS-EBs (Prsa+ 2022, VizieR J/ApJS/258/16)",
                "notes": "Primary EB signal (m_TIC=1)",
            }
        )
    frame = pd.DataFrame(rows)
    frame = frame.drop_duplicates(subset=["tic_id"], keep="first")
    logger.info("Fetched %s eclipsing binary targets", len(frame))
    return frame.reset_index(drop=True)


@retry_with_backoff(max_attempts=3, initial_delay=3.0, exceptions=(Exception,))
def fetch_starspot_candidates(limit: int = 80) -> pd.DataFrame:
    """Download rotationally variable stars from TESS rotation catalog (VizieR)."""
    logger.info("Downloading TESS rotation catalog for starspot class...")
    vizier = Vizier(columns=["TIC", "Tmag", "SNR", "Nt"])
    vizier.ROW_LIMIT = -1
    catalog = vizier.get_catalogs("J/ApJS/259/62")[0]
    rows: list[dict[str, Any]] = []
    for record in catalog:
        tic_id = normalize_tic_id(record["TIC"])
        if tic_id is None:
            continue
        snr = _safe_float(record["SNR"])
        if snr is not None and snr < 5.0:
            continue
        rows.append(
            {
                "tic_id": tic_id,
                "label": "starspot",
                "label_source": "tess_rotation_vizier",
                "label_confidence": "medium",
                "period": None,
                "depth": None,
                "duration": None,
                "snr": snr,
                "tmag": _safe_float(record["Tmag"]),
                "source_catalog": "TESS Rotation Catalog (VizieR J/ApJS/259/62)",
                "notes": "Rotationally modulated star; not a box transit",
            }
        )
    frame = pd.DataFrame(rows)
    frame = frame.drop_duplicates(subset=["tic_id"], keep="first")
    if len(frame) > limit:
        frame = frame.sample(n=limit, random_state=42).sort_values("tic_id")
    logger.info("Selected %s starspot candidates", len(frame))
    return frame.reset_index(drop=True)


@retry_with_backoff(max_attempts=3, initial_delay=3.0, exceptions=(Exception,))
def fetch_toi_false_positives(limit: int = 60) -> pd.DataFrame:
    """Download TOI false positives for blend/noise enrichment."""
    logger.info("Querying NASA Exoplanet Archive TOI table (false positives)...")
    table = NasaExoplanetArchive.query_criteria(
        table="toi",
        select="tid,toi,toidisplay,tfopwg_disp,pl_orbper",
        where="tfopwg_disp='FP'",
    )
    rows: list[dict[str, Any]] = []
    for record in table:
        tic_id = normalize_tic_id(record["tid"])
        if tic_id is None:
            continue
        period = _safe_float(record["pl_orbper"])
        rows.append(
            {
                "tic_id": tic_id,
                "toi": _safe_str(record["toi"]),
                "toidisplay": _safe_str(record["toidisplay"]),
                "label": "blend",
                "label_source": "nasa_toi_fp",
                "label_confidence": "medium",
                "period": period,
                "depth": None,
                "duration": None,
                "source_catalog": "NASA Exoplanet Archive TOI (FP)",
                "notes": "TOI false positive — likely blend or instrumental",
            }
        )
    frame = pd.DataFrame(rows)
    frame = frame.drop_duplicates(subset=["tic_id"], keep="first")
    if len(frame) > limit:
        frame = frame.sample(n=limit, random_state=42).sort_values("tic_id")
    logger.info("Fetched %s TOI false-positive targets", len(frame))
    return frame.reset_index(drop=True)


@retry_with_backoff(max_attempts=3, initial_delay=2.0, exceptions=(Exception,))
def _query_tic_patch(ra_deg: float, dec_deg: float, radius_deg: float = 0.12) -> pd.DataFrame:
    """Query TIC sources in a small sky patch."""
    position = coord.SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    table = Catalogs.query_region(position, radius=radius_deg * u.deg, catalog="TIC")
    return table.to_pandas()


@retry_with_backoff(max_attempts=2, initial_delay=1.0, exceptions=(Exception,))
def _lookup_tic_by_id(tic_id: str) -> dict[str, Any] | None:
    """Verify a TIC ID exists and return basic metadata."""
    try:
        table = Catalogs.query_criteria(catalog="TIC", ID=int(tic_id))
    except Exception:
        return None
    if len(table) == 0:
        return None
    row = table.to_pandas().iloc[0]
    tmag = _safe_float(row.get("Tmag"))
    return {"tic_id": tic_id, "Tmag": tmag, "ra": _safe_float(row.get("ra")), "dec": _safe_float(row.get("dec"))}


def _fallback_noise_from_random_ids(
    reserved_tic_ids: set[str],
    *,
    target_count: int,
    tmag_min: float,
    tmag_max: float,
    random_seed: int,
) -> list[dict[str, Any]]:
    """Probe random TIC IDs when sky-patch sampling is insufficient."""
    rng = np.random.default_rng(random_seed + 17)
    candidates: list[dict[str, Any]] = []
    seen = set(reserved_tic_ids)
    attempts = 0
    max_attempts = target_count * 40

    progress = tqdm(total=target_count, desc="Fallback TIC probing", unit="star")
    while len(candidates) < target_count and attempts < max_attempts:
        attempts += 1
        candidate_id = str(rng.integers(10_000_000, 999_999_999))
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        meta = _lookup_tic_by_id(candidate_id)
        if meta is None:
            continue
        tmag = meta.get("Tmag")
        if tmag is None or tmag < tmag_min or tmag > tmag_max:
            continue
        candidates.append(
            {
                "tic_id": candidate_id,
                "label": "noise",
                "label_source": "tic_random_probe",
                "label_confidence": "low",
                "period": None,
                "depth": None,
                "duration": None,
                "tmag": tmag,
                "ra": meta.get("ra"),
                "dec": meta.get("dec"),
                "source_catalog": "TESS Input Catalog random probe",
                "notes": "Quiet star validated via direct TIC lookup",
            }
        )
        progress.update(1)
    progress.close()
    return candidates


def generate_noise_sample(
    reserved_tic_ids: set[str],
    *,
    target_count: int = 80,
    tmag_min: float = 8.0,
    tmag_max: float = 13.0,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate noise-class TIC list from quiet field stars."""
    logger.info(
        "Generating noise-class sample (target=%s, Tmag=[%.1f, %.1f])...",
        target_count,
        tmag_min,
        tmag_max,
    )
    rng = np.random.default_rng(random_seed)
    patches = list(NOISE_SKY_PATCHES)
    rng.shuffle(patches)

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set(reserved_tic_ids)

    patch_iter = tqdm(patches, desc="Scanning sky patches", unit="patch")
    for ra_deg, dec_deg in patch_iter:
        if len(candidates) >= target_count * 2:
            break
        try:
            patch_df = _query_tic_patch(ra_deg, dec_deg)
        except Exception as exc:
            logger.warning("Sky patch (RA=%.1f, Dec=%.1f) failed: %s", ra_deg, dec_deg, exc)
            continue
        if patch_df.empty:
            continue
        patch_df = patch_df.dropna(subset=["ID", "Tmag"])
        patch_df["tic_id"] = patch_df["ID"].apply(normalize_tic_id)
        patch_df = patch_df.dropna(subset=["tic_id"])
        patch_df["Tmag"] = pd.to_numeric(patch_df["Tmag"], errors="coerce")
        patch_df = patch_df[
            (patch_df["Tmag"] >= tmag_min)
            & (patch_df["Tmag"] <= tmag_max)
            & (~patch_df["tic_id"].isin(seen))
        ]
        for _, row in patch_df.iterrows():
            tic_id = row["tic_id"]
            if tic_id in seen:
                continue
            seen.add(tic_id)
            candidates.append(
                {
                    "tic_id": tic_id,
                    "label": "noise",
                    "label_source": "tic_field_sample",
                    "label_confidence": "low",
                    "period": None,
                    "depth": None,
                    "duration": None,
                    "tmag": float(row["Tmag"]),
                    "ra": float(row["ra"]) if "ra" in row and pd.notna(row["ra"]) else None,
                    "dec": float(row["dec"]) if "dec" in row and pd.notna(row["dec"]) else None,
                    "source_catalog": "TESS Input Catalog field sample",
                    "notes": f"Quiet field star from patch RA={ra_deg:.1f}, Dec={dec_deg:.1f}",
                }
            )
            if len(candidates) >= target_count * 2:
                break

    if len(candidates) < target_count:
        logger.warning(
            "Sky patches yielded %s/%s noise candidates; running fallback TIC probing",
            len(candidates),
            target_count,
        )
        needed = target_count - len(candidates)
        fallback = _fallback_noise_from_random_ids(
            seen,
            target_count=needed,
            tmag_min=tmag_min,
            tmag_max=tmag_max,
            random_seed=random_seed,
        )
        candidates.extend(fallback)

    frame = pd.DataFrame(candidates)
    if frame.empty:
        logger.warning("No noise candidates found from sky patches")
        return frame
    if len(frame) > target_count:
        frame = frame.sample(n=target_count, random_state=random_seed).sort_values("tic_id")
    logger.info("Generated %s noise-class targets", len(frame))
    return frame.reset_index(drop=True)


def save_catalog_frame(frame: pd.DataFrame, path: Path) -> Path:
    """Persist a catalog dataframe to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    logger.info("Saved %s rows → %s", len(frame), path)
    return path


def load_catalog_frame(path: Path) -> pd.DataFrame:
    """Load a catalog CSV if it exists."""
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")
    frame = pd.read_csv(path, dtype={"tic_id": str})
    frame["tic_id"] = frame["tic_id"].apply(normalize_tic_id)
    frame = frame.dropna(subset=["tic_id"])
    return frame


def build_benchmark_targets(planet_catalog: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build benchmark_targets.csv from well-known systems enriched with catalog ephemerides."""
    rows: list[dict[str, Any]] = []
    catalog_lookup: dict[str, pd.Series] = {}
    if planet_catalog is not None and not planet_catalog.empty:
        for _, row in planet_catalog.iterrows():
            catalog_lookup[str(row["tic_id"])] = row

    for priority, system in enumerate(BENCHMARK_SYSTEMS, start=1):
        tic_id = system["tic_id"]
        catalog_row = catalog_lookup.get(tic_id)
        rows.append(
            {
                "tic_id": tic_id,
                "display_name": system["display_name"],
                "host_name": system["host_name"],
                "label": system["label"],
                "period": catalog_row["period"] if catalog_row is not None else None,
                "depth": catalog_row["depth"] if catalog_row is not None else None,
                "duration": catalog_row["duration"] if catalog_row is not None else None,
                "notes": system["notes"],
                "benchmark_priority": priority,
                "source_catalog": "ExoScan-AI curated benchmark list",
                "created_at": _utc_now(),
            }
        )
    return pd.DataFrame(rows)


def deduplicate_candidates(catalogs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge class catalogs and deduplicate by TIC with label priority."""
    combined: list[pd.DataFrame] = []
    for label, frame in catalogs.items():
        if frame is None or frame.empty:
            logger.warning("Catalog '%s' is empty — skipping", label)
            continue
        working = frame.copy()
        working["tic_id"] = working["tic_id"].apply(normalize_tic_id)
        working = working.dropna(subset=["tic_id"])
        if "label" not in working.columns:
            working["label"] = label
        combined.append(working)

    if not combined:
        return pd.DataFrame()

    merged = pd.concat(combined, ignore_index=True, sort=False)
    merged["priority"] = merged["label"].map(LABEL_PRIORITY).fillna(99)
    merged = merged.sort_values(["tic_id", "priority"])
    deduped = merged.drop_duplicates(subset=["tic_id"], keep="first").drop(columns=["priority"])
    logger.info(
        "Deduplicated %s → %s unique TIC targets",
        len(merged),
        len(deduped),
    )
    return deduped.reset_index(drop=True)


def build_training_labels(
    deduped: pd.DataFrame,
    *,
    class_targets: dict[str, int] | None = None,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Create training_labels.csv rows from deduplicated catalog entries."""
    if deduped.empty:
        return pd.DataFrame()

    targets = class_targets or {
        "transit": 80,
        "binary": 60,
        "blend": 40,
        "starspot": 60,
        "noise": 80,
    }

    selected_frames: list[pd.DataFrame] = []
    for label, count in targets.items():
        subset = deduped[deduped["label"] == label].copy()
        if subset.empty:
            logger.warning("No candidates for class '%s'", label)
            continue
        if len(subset) > count:
            subset = subset.sample(n=count, random_state=random_seed).sort_values("tic_id")
        selected_frames.append(subset)
        logger.info("Selected %s/%s targets for class '%s'", len(subset), count, label)

    selected = pd.concat(selected_frames, ignore_index=True) if selected_frames else deduped.copy()
    rows: list[dict[str, Any]] = []
    for _, record in selected.sort_values(["label", "tic_id"]).iterrows():
        tic_id = str(record["tic_id"])
        rows.append(
            {
                "sample_id": f"TIC_{tic_id}_001",
                "tic_id": tic_id,
                "label": record["label"],
                "label_source": record.get("label_source", "unknown"),
                "label_confidence": record.get("label_confidence", "medium"),
                "period": record.get("period"),
                "depth": record.get("depth"),
                "duration": record.get("duration"),
                "snr": record.get("snr"),
                "sector": record.get("sector"),
                "n_observations": 0,
                "source_catalog": record.get("source_catalog", ""),
                "raw_path": f"data/raw/{tic_id}.npz",
                "processed_path": None,
                "feature_path": None,
                "notes": record.get("notes"),
                "created_at": _utc_now(),
            }
        )
    return pd.DataFrame(rows)
