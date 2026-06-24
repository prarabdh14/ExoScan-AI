"""Domain dataclasses for ExoScan-AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray


class LabelClass(str, Enum):
    """Five-class classification labels."""

    TRANSIT = "transit"
    BINARY = "binary"
    BLEND = "blend"
    STARSPOT = "starspot"
    NOISE = "noise"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


@dataclass
class LightCurveRecord:
    """Standardized TESS light curve container."""

    tic_id: str
    time: NDArray[np.floating]
    flux: NDArray[np.floating]
    flux_err: NDArray[np.floating] | None = None
    sector: int | None = None
    mission: str = "TESS"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.time) != len(self.flux):
            raise ValueError("time and flux must have the same length")
        if self.flux_err is not None and len(self.flux_err) != len(self.flux):
            raise ValueError("flux_err must match flux length when provided")

    @property
    def n_points(self) -> int:
        return len(self.time)


@dataclass
class DetectionCandidate:
    """Output of BLS transit detection (Phase 4)."""

    period: float
    duration: float
    epoch: float
    depth: float
    detection_power: float
    snr: float
    n_transits_observed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureVector:
    """Extracted features for classification (Phase 5)."""

    sample_id: str
    tic_id: str
    features: dict[str, float]
    label: LabelClass | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        row = {"sample_id": self.sample_id, "tic_id": self.tic_id, **self.features}
        if self.label is not None:
            row["label"] = self.label.value
        return row


@dataclass
class ClassificationResult:
    """XGBoost prediction output."""

    predicted_class: LabelClass
    probabilities: dict[str, float]
    confidence: float
    model_name: str = "xgboost"

    @property
    def top_class(self) -> str:
        return self.predicted_class.value


@dataclass
class ParameterEstimate:
    """Refined transit parameters (Phase 8)."""

    period: float
    depth: float
    duration: float
    snr: float
    period_uncertainty: float | None = None
    depth_uncertainty: float | None = None
    duration_uncertainty: float | None = None


@dataclass
class CalibratedConfidence:
    """Calibrated probability scores."""

    probabilities: dict[str, float]
    confidence: float
    calibration_method: str = "isotonic"


@dataclass
class SHAPFeatureContribution:
    feature_name: str
    shap_value: float


@dataclass
class SHAPExplanation:
    """SHAP explainability output (Phase 9)."""

    predicted_class: LabelClass
    base_value: float
    contributions: list[SHAPFeatureContribution]

    def top_features(self, k: int = 5) -> list[SHAPFeatureContribution]:
        ranked = sorted(self.contributions, key=lambda c: abs(c.shap_value), reverse=True)
        return ranked[:k]


@dataclass
class PipelineResult:
    """End-to-end pipeline output."""

    target_id: str
    raw_lc: LightCurveRecord | None = None
    processed_lc: LightCurveRecord | None = None
    detection: DetectionCandidate | None = None
    features: FeatureVector | None = None
    classification: ClassificationResult | None = None
    parameters: ParameterEstimate | None = None
    confidence: CalibratedConfidence | None = None
    shap: SHAPExplanation | None = None
    errors: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class TrainingSample:
    """One row in the training dataset (see docs/dataset_schema.md)."""

    sample_id: str
    tic_id: str
    label: LabelClass
    label_source: str
    label_confidence: str
    period: float | None
    depth: float | None
    duration: float | None
    snr: float | None
    sector: int | None
    n_observations: int
    source_catalog: str
    raw_path: str | None = None
    processed_path: str | None = None
    feature_path: str | None = None
    notes: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "tic_id": self.tic_id,
            "label": self.label.value,
            "label_source": self.label_source,
            "label_confidence": self.label_confidence,
            "period": self.period,
            "depth": self.depth,
            "duration": self.duration,
            "snr": self.snr,
            "sector": self.sector,
            "n_observations": self.n_observations,
            "source_catalog": self.source_catalog,
            "raw_path": self.raw_path,
            "processed_path": self.processed_path,
            "feature_path": self.feature_path,
            "notes": self.notes,
            "created_at": self.created_at,
        }
