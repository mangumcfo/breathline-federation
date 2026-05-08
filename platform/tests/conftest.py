"""Shared pytest fixtures for the Breathline Agentic Platform test suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so tests can import kernel/, platform/, etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def seed_dir() -> Path:
    """Path to the seed/ directory containing the locked spec files."""
    return PROJECT_ROOT / "seed"


@pytest.fixture
def fingerprints_path(seed_dir: Path) -> Path:
    """Path to the published fingerprints file generated at scaffolding time."""
    return seed_dir / ".fingerprints.json"
