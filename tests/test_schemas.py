"""Phase 0 config loader smoke test."""

from exoscan.config import load_config
from exoscan.data.schemas import LabelClass


def test_load_config():
    config = load_config()
    assert config.project.name == "ExoScan-AI"
    assert len(config.class_labels) == 5


def test_label_enum():
    assert LabelClass.TRANSIT.value == "transit"
    assert len(LabelClass.values()) == 5
