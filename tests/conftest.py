"""Shared pytest fixtures — expand in later phases."""

import pytest


@pytest.fixture
def project_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[1]
