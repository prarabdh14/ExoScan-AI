"""YAML configuration loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "configs"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass
class ProjectConfig:
    name: str = "ExoScan-AI"
    version: str = "0.1.0"
    random_seed: int = 42


@dataclass
class PathsConfig:
    raw_data: str = "data/raw"
    processed_data: str = "data/processed"
    features: str = "data/features"
    labels: str = "data/labels"
    external: str = "data/external"
    models: str = "models"
    reports: str = "reports"

    def resolve(self, root: Path | None = None) -> PathsConfig:
        base = root or PROJECT_ROOT
        return PathsConfig(
            raw_data=str((base / self.raw_data).resolve()),
            processed_data=str((base / self.processed_data).resolve()),
            features=str((base / self.features).resolve()),
            labels=str((base / self.labels).resolve()),
            external=str((base / self.external).resolve()),
            models=str((base / self.models).resolve()),
            reports=str((base / self.reports).resolve()),
        )


@dataclass
class ExoScanConfig:
    """Top-level configuration container."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    data: dict[str, Any] = field(default_factory=dict)
    preprocessing: dict[str, Any] = field(default_factory=dict)
    detection: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] = field(default_factory=dict)
    dashboard: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def class_labels(self) -> list[str]:
        return list(self.classification.get("classes", []))

    def ensure_directories(self, root: Path | None = None) -> None:
        base = root or PROJECT_ROOT
        for relative_path in (
            self.paths.raw_data,
            self.paths.processed_data,
            self.paths.features,
            self.paths.labels,
            self.paths.external,
            self.paths.models,
            self.paths.reports,
        ):
            path = Path(relative_path)
            target = path if path.is_absolute() else base / path
            target.mkdir(parents=True, exist_ok=True)


def load_config(config_dir: Path | None = None) -> ExoScanConfig:
    """Load and merge all YAML config files from configs/."""
    config_path = config_dir or CONFIG_DIR

    base = _load_yaml(config_path / "base.yaml")
    data = _load_yaml(config_path / "data.yaml")
    preprocessing = _load_yaml(config_path / "preprocessing.yaml")
    detection = _load_yaml(config_path / "detection.yaml")
    classification = _load_yaml(config_path / "classification.yaml")
    dashboard = _load_yaml(config_path / "dashboard.yaml")

    merged = _deep_merge(base, data)
    merged = _deep_merge(merged, preprocessing)
    merged = _deep_merge(merged, detection)
    merged = _deep_merge(merged, classification)
    merged = _deep_merge(merged, dashboard)

    project_data = merged.get("project", {})
    paths_data = merged.get("paths", {})

    data_section = {
        key: merged[key]
        for key in ("download", "sectors", "catalogs", "dataset_builder", "class_targets")
        if key in merged
    }

    return ExoScanConfig(
        project=ProjectConfig(
            name=project_data.get("name", "ExoScan-AI"),
            version=project_data.get("version", "0.1.0"),
            random_seed=project_data.get("random_seed", 42),
        ),
        paths=PathsConfig(**paths_data) if paths_data else PathsConfig(),
        data=data_section,
        preprocessing={
            key: merged[key]
            for key in (
                "pipeline",
                "missing_values",
                "outlier_removal",
                "flux_normalization",
                "savgol_smoothing",
                "median_filter",
            )
            if key in merged
        },
        detection={
            key: merged[key] for key in ("bls", "validation") if key in merged
        },
        classification={
            key: merged[key]
            for key in ("model", "xgboost", "training", "calibration", "classes")
            if key in merged
        },
        dashboard={
            key: merged[key] for key in ("app", "defaults", "cache", "theme") if key in merged
        },
        logging=merged.get("logging", {}),
        raw=merged,
    )
