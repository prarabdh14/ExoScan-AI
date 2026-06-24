# Phase 1: Dataset Acquisition

This guide covers downloading labeled target lists for ExoScan-AI **without** downloading light curves yet (Phase 2).

## Quick Start

```bash
# From project root
source .venv/bin/activate
pip install -r requirements.txt

# Step 1: Download all external catalogs (~5–15 min depending on network)
make download-catalogs
# or: PYTHONPATH=src python scripts/download_catalogs.py

# Step 2: Build deduplicated label files
make build-labels
# or: PYTHONPATH=src python scripts/build_training_labels.py
```

## Outputs

| File | Description |
|------|-------------|
| `data/external/nasa_confirmed_planets.csv` | TESS confirmed exoplanets (transit class) |
| `data/external/tess_ebs_catalog.csv` | TESS Eclipsing Binaries (binary class) |
| `data/external/rotation_catalog.csv` | Rotation variables (starspot class) |
| `data/external/toi_blend_flags.csv` | TOI false positives (blend class) |
| `data/external/quiet_star_sample.csv` | Quiet field stars (noise class) |
| `data/external/deduplicated_candidates.csv` | Merged catalog after deduplication |
| `data/labels/training_labels.csv` | Master training label table |
| `data/labels/benchmark_targets.csv` | 12 well-known exoplanet systems for evaluation |

## Catalog Sources

### Transit — NASA Exoplanet Archive
- **Table:** `pscomppars`
- **Filter:** `disc_facility like '%TESS%'`
- **Labels:** High confidence confirmed planets
- **Columns used:** `tic_id`, `pl_orbper`, `pl_trandep`, `pl_trandur`

### Binary — TESS-EBs (VizieR)
- **Catalog:** `J/ApJS/258/16/tess-ebs` (Prša et al. 2022)
- **Filter:** Primary signal only (`m_TIC = 1`)
- **Expected rows:** ~4,500

### Starspot — TESS Rotation Catalog (VizieR)
- **Catalog:** `J/ApJS/259/62`
- **Filter:** SNR ≥ 5
- **Label confidence:** Medium

### Blend — NASA TOI False Positives
- **Table:** `toi` with `tfopwg_disp='FP'`
- **Label confidence:** Medium (vetting-based)

### Noise — TIC Field Sample
- **Method:** Query TIC in 8 southern ecliptic sky patches
- **Filter:** Tmag 9–12, exclude all catalog targets above
- **Label confidence:** Low

## Deduplication Priority

When a TIC appears in multiple catalogs:

```
transit > binary > blend > starspot > noise
```

## Configuration

Per-class target counts in `configs/data.yaml`:

```yaml
class_targets:
  transit: 80
  binary: 60
  blend: 40
  starspot: 60
  noise: 80
```

## CLI Options

### download_catalogs.py

| Flag | Description |
|------|-------------|
| `--output-dir` | Catalog output directory (default: `data/external`) |
| `--skip-noise` | Skip noise generation (faster for testing) |
| `--noise-count N` | Override noise class count |
| `--log-level` | DEBUG, INFO, WARNING, ERROR |

### build_training_labels.py

| Flag | Description |
|------|-------------|
| `--external-dir` | Input catalog directory |
| `--labels-dir` | Output label directory |
| `--include-benchmark-in-training` | Keep benchmark TICs in training set |

## Retry Logic

All network queries use exponential backoff (3 attempts, 2–8 s delays). Failures are logged with the function name and attempt count.

## Next Step

After Phase 1 completes, proceed to **Phase 2: TESS Loader** to download light curves for TIC IDs listed in `training_labels.csv`.
