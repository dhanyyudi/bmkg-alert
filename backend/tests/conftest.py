"""Pytest configuration and fixtures."""

import json
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture(fixtures_dir):
    """Load a fixture file."""
    def _load(name: str):
        path = fixtures_dir / name
        with open(path, "r") as f:
            if name.endswith(".json"):
                return json.load(f)
            return f.read()
    return _load


@pytest.fixture
def sample_autogempa(load_fixture):
    """Sample autogempa response."""
    return load_fixture("autogempa.json")


@pytest.fixture
def sample_gempaterkini(load_fixture):
    """Sample gempaterkini response."""
    return load_fixture("gempaterkini.json")


@pytest.fixture
def sample_gempadirasakan(load_fixture):
    """Sample gempadirasakan response."""
    return load_fixture("gempadirasakan.json")


@pytest.fixture
def sample_rss_active(load_fixture):
    """Sample RSS active warnings feed."""
    return load_fixture("rss_active.xml")


@pytest.fixture
def sample_cap_banten(load_fixture):
    """Sample CAP XML for Banten."""
    return load_fixture("cap_banten.xml")


@pytest.fixture
def sample_cap_jateng(load_fixture):
    """Sample CAP XML for Jawa Tengah."""
    return load_fixture("cap_jateng.xml")


@pytest.fixture
def sample_forecast(load_fixture):
    """Sample weather forecast response."""
    return load_fixture("forecast_response.json")
