# Training Dataset Acquisition Plan

This document is the **critical path** for ExoScan-AI. Labels do not ship with raw TESS light curves — they must be assembled from public catalogs and vetting flags.

## MVP Target: ~320 labeled samples

| Class | Target N | Minimum N |
|-------|----------|-----------|
| transit | 80 | 60 |
| binary | 60 | 40 |
| blend | 40 | 25 |
| starspot | 60 | 40 |
| noise | 80 | 60 |

---

## Class 1: Transit (Exoplanet)

| Field | Detail |
|-------|--------|
| **Data source** | TESS 2-min / 30-min light curves via MAST |
| **Download method** | `lightkurve.search_lightcurve(tic, mission="TESS")` |
| **Label source** | [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/) — `pscomppars` table, filter `disc_facility LIKE '%TESS%'` and `pl_tranflag=1` |
| **Secondary label source** | TESS Objects of Interest (TOI) with `tfopwg_disp = CP` (Confirmed Planet) |
| **Label rule** | TIC appears in confirmed planet table with published period |
| **Expected examples** | 80–120 (archive has 100+ TESS confirmed planets) |
| **Storage** | Raw: `data/raw/{tic_id}_s{sector}.npz` · Catalog: `data/external/nasa_confirmed_planets.csv` |

**Acquisition script (Phase 1):**
1. Query `pscomppars` via `astroquery.nasa_exoplanet_archive.NasaExoplanetArchive`
2. Cross-match `hostname` / `tic_id` column to TIC
3. Write row to `training_labels.csv` with `label=transit`, `label_confidence=high`
4. Copy catalog period/depth/duration where available

---

## Class 2: Eclipsing Binary

| Field | Detail |
|-------|--------|
| **Data source** | TESS light curves |
| **Download method** | Same `lightkurve` pipeline |
| **Label source** | [TESS EBS Catalog](https://www.tessEBcatalog.org/) — ~5,000 EBs with TIC IDs |
| **Secondary label source** | Villanova EB catalog cross-matched to TIC; or TESS CP objects with `pl_tranflag=0` and EB flag in TIC v8 |
| **Label rule** | TIC in TESS EBS catalog with known period; exclude targets also in confirmed planet table |
| **Expected examples** | 60–80 |
| **Storage** | Raw NPZ + `data/external/tess_ebs_catalog.csv` |

**Notes:** EBs have deeper, often V-shaped eclipses — strong BLS signals. Prefer short-period (< 5 d) EBs for clear multi-transit coverage in one sector.

---

## Class 3: Stellar Blend

| Field | Detail |
|-------|--------|
| **Data source** | TESS light curves |
| **Download method** | `lightkurve` |
| **Label source** | TESS TOI vetting reports with disposition `FP` + reason containing "multi-source", "blend", "diluted", or "contamination" |
| **Secondary label source** | TIC v8 `Contamination` field > 0.3; or ExoFOP blend flags |
| **Label rule** | Manual review of 40–50 candidates from TOI false-positive table; keep only blend/contamination cases |
| **Expected examples** | 40–50 (hardest class — expect manual curation) |
| **Storage** | Raw NPZ + `data/external/toi_blend_flags.csv` with vetting notes |

**Fallback if blend count is low:** Merge under-represented blend examples into `binary` for training only, but keep separate label in CSV for future relabeling. Report honestly in model card.

---

## Class 4: Starspot Activity

| Field | Detail |
|-------|--------|
| **Data source** | TESS light curves |
| **Download method** | `lightkurve` |
| **Label source** | TESS rotation period catalog (McQuillan et al. style tables via MAST/TIC); targets with `Prot < 15 d` and significant flux modulation |
| **Secondary label source** | TIC `VarType` containing "RR", "RS", "BY", or "Rot" |
| **Label rule** | Significant periodic variability (Lomb-Scargle peak) but **no box-shaped transit**; exclude if in planet/EB catalogs |
| **Expected examples** | 60–80 |
| **Storage** | Raw NPZ + `data/external/rotation_catalog.csv` |

**Validation:** Visual check — quasi-sinusoidal modulation, asymmetric dips, no clean flat out-of-transit baseline.

---

## Class 5: Noise / False Positive

| Field | Detail |
|-------|--------|
| **Data source** | TESS light curves |
| **Download method** | `lightkurve` |
| **Label source** | Random TIC sample from TIC-8 with `VarType = "NONE"` and not in any exoplanet/EB catalog |
| **Secondary label source** | TOI false positives flagged as "instrumental" or "stellar variability" (non-periodic); BLS run on quiet stars yielding low-power spurious peaks |
| **Label rule** | No entry in planet/EB catalogs; flat or random noise-dominated LC; if BLS triggered, power < threshold |
| **Expected examples** | 80–100 |
| **Storage** | Raw NPZ + `data/external/quiet_star_sample.csv` |

**Augmentation strategy:** Run BLS on 50 quiet stars; label detections with power < 4σ as `noise` even if BLS peaks exist — teaches classifier to reject weak false positives.

---

## Phase 1 Acquisition Workflow

```
Day 1 Morning (Both devs, 2h)
  └── Agree on label definitions + schema

Day 1 (Dev 1)
  ├── Pull NASA confirmed planets CSV        → 80 transit TICs
  ├── Pull TESS EBS catalog                  → 60 binary TICs
  └── Pull rotation variable list            → 60 starspot TICs

Day 1 (Dev 2)
  ├── Pull TOI FP blend flags                → 40 blend TICs
  ├── Sample 80 quiet TICs from TIC-8        → noise class
  └── Deduplicate: remove TICs in multiple catalogs (priority: transit > binary > blend > starspot)

Day 1–2 (Dev 2)
  └── Batch download all TICs → data/raw/*.npz

Day 2 (Dev 1)
  └── Manual QA: spot-check 5 per class; flag bad downloads in notes column
```

---

## Deduplication Priority

If a TIC appears in multiple catalogs, assign:

1. `transit` (confirmed planet)
2. `binary` (EB catalog)
3. `blend` (vetting flag)
4. `starspot` (rotation)
5. `noise` (default for unlabeled quiet stars)

---

## Storage Layout

```
data/
├── raw/                          # One NPZ per TIC (all sectors stitched or best sector)
│   └── {tic_id}.npz              # arrays: time, flux, flux_err, sector, meta_*
├── processed/                    # After preprocessing (Phase 3)
│   └── {tic_id}_processed.npz
├── external/                     # Catalog CSVs (label provenance)
│   ├── nasa_confirmed_planets.csv
│   ├── tess_ebs_catalog.csv
│   ├── toi_blend_flags.csv
│   ├── rotation_catalog.csv
│   └── quiet_star_sample.csv
├── labels/
│   └── training_labels.csv       # Master label table (one row per sample)
└── features/
    └── training_features.parquet # Feature matrix (Phase 6)
```

---

## Label Confidence Levels

| Level | Meaning |
|-------|---------|
| `high` | Confirmed in authoritative catalog (planet, EB) |
| `medium` | Catalog flag + manual visual check passed |
| `low` | Heuristic only (e.g., quiet star sample); use for noise class |

Store in `label_confidence` column. Training can weight or filter `low` confidence if needed.
