# Implementation Roadmap

Lean MVP for 2-developer ISRO Hackathon team. No deep learning, no RF comparison, no CI/CD.

---

## Phase 0 — Repository Scaffold ✅

**Goal:** Shared contracts, configs, schemas.

**Deliverables:**
- Repo structure, `requirements.txt`, YAML configs
- Dataclasses: `LightCurveRecord`, `PipelineResult`, `TrainingSample`, etc.
- Config loader, smoke tests

**Exit criteria:** `make config-check` passes; both devs can import `exoscan`.

---

## Phase 1 — Dataset Acquisition

**Goal:** ~320 labeled TIC IDs with catalog provenance.

**Owner:** Dev 1 (catalogs) + Dev 2 (downloads)

**Deliverables:**
- `data/external/*.csv` (5 catalog files)
- `data/labels/training_labels.csv` populated
- `scripts/download_data.py` batch download → `data/raw/*.npz`
- QA checklist: 5 visual checks per class

**Exit criteria:** ≥60 transit, ≥40 binary, ≥25 blend, ≥40 starspot, ≥60 noise rows.

---

## Phase 2 — TESS Loader

**Goal:** Standardized light curve loading.

**Owner:** Dev 2

**Deliverables:**
- `src/exoscan/data/loader.py` — `load_light_curve(tic_id) → LightCurveRecord`
- Local NPZ cache read/write
- `lightkurve` fallback download

**Exit criteria:** Load 3 demo targets from `demo_catalog.csv` without error.

---

## Phase 3 — Preprocessing

**Goal:** Denoise and normalize light curves.

**Owner:** Dev 2

**Deliverables:**
- Modular steps: missing, outliers, normalize, Savitzky-Golay, median filter
- `PreprocessingPipeline.run(lc) → LightCurveRecord`
- Save to `data/processed/`

**Exit criteria:** Before/after plot in notebook; unit test on synthetic LC.

---

## Phase 4 — BLS Detection

**Goal:** Periodic dip detection via astropy BLS.

**Owner:** Dev 1

**Deliverables:**
- `src/exoscan/detection/bls.py` — `BLSDetector.detect(lc) → DetectionCandidate`
- Periodogram export for visualization
- Multi-transit validator

**Exit criteria:** Recover TOI-700 period within 5% on processed LC.

---

## Phase 5 — Feature Extraction

**Goal:** ~15 features per detection.

**Owner:** Dev 1

**Deliverables:**
- `src/exoscan/features/extractor.py`
- Feature registry with documented formulas

**Exit criteria:** Feature dict returned for one known transit; no NaN on demo set.

---

## Phase 6 — Dataset Builder

**Goal:** Full feature matrix for training.

**Owner:** Dev 1

**Deliverables:**
- `scripts/build_training_set.py`
- `data/features/training_features.parquet`
- Stratified train/val/test split column

**Exit criteria:** Parquet with ≥250 rows, all 5 classes present.

---

## Phase 7 — XGBoost Training

**Goal:** Trained, calibrated classifier.

**Owner:** Dev 1

**Deliverables:**
- `src/exoscan/classification/xgboost_model.py`
- `scripts/train_models.py`
- `models/xgboost/classifier.joblib` + `metadata.json`
- Macro-F1 report in `reports/metrics/`

**Exit criteria:** Macro-F1 ≥ 0.60 on held-out test set.

---

## Phase 8 — Parameter Estimation

**Goal:** Refined period, depth, duration, SNR.

**Owner:** Dev 1

**Deliverables:**
- `src/exoscan/estimation/parameters.py`
- Refinement on folded, processed LC

**Exit criteria:** Period MAE < 5% on transit class test samples.

---

## Phase 9 — SHAP Explainability

**Goal:** Per-prediction feature attributions.

**Owner:** Dev 1

**Deliverables:**
- `src/exoscan/explainability/shap_explainer.py`
- Standard output: prediction, confidence, top-5 features

**Exit criteria:** SHAP waterfall data generated for demo transit.

---

## Phase 10 — Streamlit Dashboard

**Goal:** Polished 8-page demo.

**Owner:** Dev 2 (+ Dev 1 integration support)

**Deliverables:**
- `dashboard/app.py` + 8 pages
- `src/exoscan/pipeline/orchestrator.py` — end-to-end `run(tic_id)`
- `src/exoscan/visualization/*` — Plotly figure builders
- Pre-cached demo targets

**Exit criteria:** 5-minute demo flow works offline; all 8 pages render.

---

## Dependency Graph

```
Phase 0
  ↓
Phase 1 (Dataset) ─────────────────────────────┐
  ↓                                            │
Phase 2 (Loader) → Phase 3 (Preprocess)        │
                       ↓                       │
                  Phase 4 (BLS)                │
                       ↓                       │
                  Phase 5 (Features)           │
                       ↓                       │
                  Phase 6 (Dataset Builder) ←──┘
                       ↓
                  Phase 7 (XGBoost)
                       ↓
              Phase 8 (Params) + Phase 9 (SHAP)
                       ↓
                  Phase 10 (Dashboard)
```

---

## Timeline (4-Day Hackathon)

| Day | Dev 1 | Dev 2 |
|-----|-------|-------|
| 1 | Phase 1 catalogs + Phase 4 BLS start | Phase 1 downloads + Phase 2 loader |
| 2 | Phase 4–5 features | Phase 3 preprocessing |
| 3 | Phase 6–7 train XGBoost | Phase 10 dashboard shell + viz |
| 4 | Phase 8–9 params + SHAP | Phase 10 integration + demo polish |
