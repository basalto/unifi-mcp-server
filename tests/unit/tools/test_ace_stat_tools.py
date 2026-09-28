"""Unit tests for ace_stat analytics tools (ace-stat-api sidecar bridge)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.tools.ace_stat as ace_stat
from src.tools.ace_stat import get_ace_stat_health, get_dpi_analytics, get_wan_health_history


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.log_level = "INFO"
    settings.ace_stat_url = "http://192.168.1.101:8787"
    return settings


def _mock_httpx(json_value):
    client = MagicMock()
    client.get = AsyncMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_value
    client.get.return_value = resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ---------------------------------------------------------------------------
# _client / _get behaviour
# ---------------------------------------------------------------------------


@patch("src.tools.ace_stat.httpx.AsyncClient")
def test_client_unset_url_raises(AsyncClientMock):
    settings = MagicMock()
    settings.ace_stat_url = None
    with pytest.raises(RuntimeError, match="ACE_STAT_URL"):
        ace_stat._client(settings)


# ---------------------------------------------------------------------------
# get_ace_stat_health
# ---------------------------------------------------------------------------


@patch("src.tools.ace_stat.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_get_ace_stat_health(AsyncClientMock, mock_settings):
    client = _mock_httpx({"status": "ok", "collections": {"stat_daily": 340}})
    AsyncClientMock.return_value = client
    result = await get_ace_stat_health(mock_settings)
    assert result["status"] == "ok"
    assert result["collections"]["stat_daily"] == 340


@patch("src.tools.ace_stat.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_get_ace_stat_health_error(AsyncClientMock, mock_settings):
    client = MagicMock()
    resp = MagicMock()
    resp.status_code = 502
    resp.text = "boom"
    client.get = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    AsyncClientMock.return_value = client
    with pytest.raises(RuntimeError, match="502"):
        await get_ace_stat_health(mock_settings)


# ---------------------------------------------------------------------------
# get_dpi_analytics
# ---------------------------------------------------------------------------


@patch("src.tools.ace_stat.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_get_dpi_analytics_passes_range_and_hours(AsyncClientMock, mock_settings):
    client = _mock_httpx({"applications": [], "categories": [], "countries": []})
    AsyncClientMock.return_value = client
    await get_dpi_analytics(mock_settings, time_range="daily", hours=48)
    _, kwargs = client.get.call_args
    assert kwargs["params"] == {"range": "daily", "hours": 48}


@pytest.mark.asyncio
async def test_get_dpi_analytics_invalid_range(mock_settings):
    with pytest.raises(ValueError, match="time_range"):
        await get_dpi_analytics(mock_settings, time_range="bogus")


# ---------------------------------------------------------------------------
# get_wan_health_history
# ---------------------------------------------------------------------------


@patch("src.tools.ace_stat.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_get_wan_health_history(AsyncClientMock, mock_settings):
    client = _mock_httpx([{"datetime": "2026-09-27T13:00:00Z", "isp_name": "Nos"}])
    AsyncClientMock.return_value = client
    result = await get_wan_health_history(mock_settings, time_range="hourly", hours=24)
    assert result[0]["isp_name"] == "Nos"
