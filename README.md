# ExoScan-AI

AI-enabled detection and classification of exoplanet candidates from noisy TESS light curves.

## Quickstart (Phase 0)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python -c "from exoscan.config import load_config; print(load_config().project.name)"
```

## MVP Pipeline

```
TESS Loader → Preprocessing → BLS Detection → Features → XGBoost → Parameters → SHAP → Streamlit
```

## Documentation

- [Phase 1: Dataset Acquisition](docs/phase1_dataset_acquisition.md)
- [Dataset Strategy](docs/dataset_strategy.md)
- [Dataset Schema](docs/dataset_schema.md)
- [Implementation Roadmap](docs/roadmap.md)

## Team

| Developer | Focus |
|-----------|-------|
| Dev 1 | BLS, features, dataset builder, XGBoost, SHAP |
| Dev 2 | TESS loader, preprocessing, visualization, dashboard, integration |

## Status

Phase 0 scaffolding complete. Astronomy/ML algorithms not yet implemented.
