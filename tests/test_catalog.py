"""Unit tests for catalog helpers (no network)."""

import pandas as pd

from exoscan.data.catalog import (
    build_training_labels,
    deduplicate_candidates,
    normalize_tic_id,
)


def test_normalize_tic_id():
    assert normalize_tic_id("TIC 25155310") == "25155310"
    assert normalize_tic_id("25155310") == "25155310"
    assert normalize_tic_id(None) is None
    assert normalize_tic_id("  TIC-307210830  ") == "307210830"


def test_deduplicate_priority():
    catalogs = {
        "transit": pd.DataFrame(
            [{"tic_id": "100", "label": "transit", "label_source": "a", "label_confidence": "high"}]
        ),
        "binary": pd.DataFrame(
            [{"tic_id": "100", "label": "binary", "label_source": "b", "label_confidence": "high"}]
        ),
        "noise": pd.DataFrame(
            [{"tic_id": "200", "label": "noise", "label_source": "c", "label_confidence": "low"}]
        ),
    }
    deduped = deduplicate_candidates(catalogs)
    assert len(deduped) == 2
    winner = deduped.loc[deduped["tic_id"] == "100", "label"].iloc[0]
    assert winner == "transit"


def test_build_training_labels_respects_class_targets():
    deduped = pd.DataFrame(
        [
            {"tic_id": str(i), "label": "noise", "label_source": "x", "label_confidence": "low"}
            for i in range(10)
        ]
    )
    labels = build_training_labels(deduped, class_targets={"noise": 5}, random_seed=42)
    assert len(labels) == 5
    assert all(labels["label"] == "noise")
    assert labels["sample_id"].iloc[0].startswith("TIC_")
