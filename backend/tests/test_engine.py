"""Tests for the alert engine — full poll cycle with mocked BMKG client."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.engine.worker import AlertEngine
from app.models import (
    Location,
    NowcastDetailResponse,
    NowcastListResponse,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestAlertEnginePollCycle:
    """Test the engine's poll cycle logic."""

    @pytest.fixture
    def mock_bmkg_client(self):
        client = AsyncMock()
        # Load fixtures
        list_data = _load_fixture("nowcast_list.json")
        detail_data = _load_fixture("nowcast_detail.json")

        client.get_nowcast_list.return_value = NowcastListResponse(**list_data)
        client.get_nowcast_detail.return_value = NowcastDetailResponse(**detail_data)
        return client

    @pytest.fixture
    def mock_state(self):
        state = AsyncMock()
        state.get_enabled_locations.return_value = [
            Location(
                id=1,
                label="Test Location",
                province_code="33",
                province_name="Jawa Tengah",
                district_code="3305",
                district_name="Kebumen",
                subdistrict_code="330501",
                subdistrict_name="Alian",
                enabled=True,
            )
        ]
        state.get_enabled_channels.return_value = []
        state.is_duplicate.return_value = False
        state.store_alert.return_value = 1
        state.mark_expired_alerts.return_value = []
        state.get_config_value.return_value = "300"
        state.log_activity.return_value = None
        return state

    @pytest.fixture
    def mock_dispatcher(self):
        return AsyncMock()

    @pytest.fixture
    def engine(self, mock_bmkg_client, mock_state, mock_dispatcher):
        return AlertEngine(mock_bmkg_client, mock_state, mock_dispatcher)

    @pytest.mark.asyncio
    async def test_poll_cycle_finds_matches(self, engine, mock_state):
        """Poll cycle finds and stores matching alerts."""
        result = await engine.check_now()

        assert result["warnings_fetched"] == 2
        assert result["matches_found"] >= 1
        assert result["new_alerts"] >= 1
        mock_state.store_alert.assert_called()

    @pytest.mark.asyncio
    async def test_poll_cycle_dedup(self, engine, mock_state):
        """Duplicate alerts are skipped."""
        mock_state.is_duplicate.return_value = True

        result = await engine.check_now()

        assert result["duplicates_skipped"] >= 1
        assert result["new_alerts"] == 0

    @pytest.mark.asyncio
    async def test_poll_cycle_no_locations(self, engine, mock_state):
        """No locations configured — no matches."""
        mock_state.get_enabled_locations.return_value = []

        result = await engine.check_now()

        assert result["matches_found"] == 0

    @pytest.mark.asyncio
    async def test_poll_cycle_handles_api_error(self, engine, mock_bmkg_client):
        """API errors are handled gracefully."""
        mock_bmkg_client.get_nowcast_list.side_effect = Exception("API timeout")

        await engine.check_now()
        # Should not raise — errors are caught
        assert engine.last_poll_result is not None

    @pytest.mark.asyncio
    async def test_engine_start_stop(self, engine):
        """Engine can be started and stopped."""
        assert not engine.running

        await engine.start()
        assert engine.running

        await engine.stop()
        assert not engine.running

    @pytest.mark.asyncio
    async def test_engine_status(self, engine):
        """Engine status reflects current state."""
        status = engine.get_status()
        assert status["running"] is False

        await engine.start()
        status = engine.get_status()
        assert status["running"] is True

        await engine.stop()
