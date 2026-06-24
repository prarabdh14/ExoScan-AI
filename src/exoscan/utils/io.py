"""I/O helpers for NPZ and CSV artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def save_light_curve_npz(
    path: str | Path,
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Save a light curve array bundle to NPZ."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"time": time, "flux": flux}
    if flux_err is not None:
        payload["flux_err"] = flux_err
    if metadata:
        for key, value in metadata.items():
            payload[f"meta_{key}"] = np.array([value], dtype=object)
    np.savez_compressed(output, **payload)
    return output
