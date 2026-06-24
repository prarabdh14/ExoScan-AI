# Training Dataset Schema

ExoScan-AI uses **three related tables/files**. Light curve arrays are not stored inline in CSV — they live in NPZ files referenced by path.

---

## 1. Master Label Table — `data/labels/training_labels.csv`

One row per training sample (one TIC = one sample for MVP).

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `sample_id` | string | yes | Unique ID, e.g. `TIC_25155310_001` |
| `tic_id` | string | yes | TESS Input Catalog ID |
| `label` | enum | yes | `transit` \| `binary` \| `blend` \| `starspot` \| `noise` |
| `label_source` | string | yes | Catalog or rule, e.g. `nasa_pscomppars`, `tess_ebs`, `toi_vetting` |
| `label_confidence` | enum | yes | `high` \| `medium` \| `low` |
| `period` | float | no | Catalog period (days); null if unknown |
| `depth` | float | no | Catalog transit/eclipse depth (ppm or fraction) |
| `duration` | float | no | Catalog duration (hours or days — document unit in notes) |
| `snr` | float | no | Pre-computed or null until feature extraction |
| `sector` | int | no | Primary TESS sector used |
| `n_observations` | int | yes | Number of flux points in raw LC |
| `source_catalog` | string | yes | Human-readable catalog name |
| `raw_path` | string | no | Relative path to raw NPZ, e.g. `data/raw/25155310.npz` |
| `processed_path` | string | no | Filled in Phase 3 |
| `feature_path` | string | no | Filled in Phase 6 |
| `notes` | string | no | Free text (vetting reason, QA flags) |
| `created_at` | ISO datetime | yes | Row creation timestamp |

---

## 2. Light Curve NPZ — `data/raw/{tic_id}.npz`

| Array / Key | Type | Description |
|-------------|------|-------------|
| `time` | float64[n] | BJD or TESS time |
| `flux` | float64[n] | Normalized flux (raw from lightkurve) |
| `flux_err` | float64[n] | Flux uncertainty (optional) |
| `meta_tic_id` | object | TIC ID string |
| `meta_sector` | object | Sector number(s) |
| `meta_mission` | object | `"TESS"` |

---

## 3. Feature Matrix — `data/features/training_features.parquet`

One row per sample after Phase 6. Used directly by XGBoost training.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `sample_id` | string | yes | FK → training_labels.sample_id |
| `tic_id` | string | yes | TIC ID |
| `label` | enum | yes | Target class |
| **BLS features** | | | |
| `period` | float | yes | BLS best period (days) |
| `duration` | float | yes | BLS duration (days) |
| `depth` | float | yes | BLS depth (flux fraction) |
| `detection_power` | float | yes | BLS power statistic |
| `snr` | float | yes | Signal-to-noise ratio |
| `epoch` | float | yes | Transit epoch (BJD) |
| **Morphology features** | | | |
| `ingress_slope` | float | yes | Folded LC ingress slope |
| `egress_slope` | float | yes | Folded LC egress slope |
| `symmetry_ratio` | float | yes | Ingress vs egress symmetry (0–1) |
| `dip_width` | float | yes | Transit width at half depth |
| `n_transits_observed` | int | yes | Count of visible transits |
| **Variability features** | | | |
| `flux_std` | float | yes | Out-of-transit scatter |
| `duty_cycle` | float | yes | duration / period |
| `fold_residual_rms` | float | yes | RMS after folding |
| `outlier_fraction` | float | yes | Fraction of clipped points |
| `gap_fraction` | float | yes | Fraction of interpolated gaps |
| **Split columns** | | | |
| `split` | enum | yes | `train` \| `val` \| `test` |
| `created_at` | ISO datetime | yes | Feature extraction timestamp |

---

## 4. Demo Catalog — `data/labels/demo_catalog.csv`

Curated targets for Streamlit demo (pre-cached, no live MAST dependency during judging).

| Column | Type | Description |
|--------|------|-------------|
| `tic_id` | string | TIC ID |
| `display_name` | string | Human name, e.g. `TOI-700` |
| `label` | enum | Expected ground truth |
| `notes` | string | Demo talking points |
| `demo_priority` | int | Sort order in dashboard dropdown |

---

## Entity Relationships

```
training_labels.csv (1) ──→ (1) raw/{tic_id}.npz
training_labels.csv (1) ──→ (0..1) processed/{tic_id}_processed.npz
training_labels.csv (1) ──→ (1) training_features.parquet row
demo_catalog.csv        ──→ subset of training_labels + pre-cached NPZ
```

---

## Sample ID Convention

```
TIC_{tic_id}_{sequence:03d}
```

Example: `TIC_25155310_001`

---

## Train / Val / Test Split

- Stratified by `label` (preserve class ratios)
- Default: 70% / 15% / 15%
- Split assigned in Phase 6 and stored in `training_features.parquet` → column `split`
- Same TIC must not appear in multiple splits (one sample per TIC for MVP)
