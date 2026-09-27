"""ace_stat analytics tools — read-only bridge over the ace-stat-api sidecar.

These tools expose historical controller analytics that the legacy UniFi API
does not serve: per-app/category DPI bandwidth (with names resolved from the
controller's DPI catalog), per-country traffic, WAN/LAN health history, client
WiFi quality, downtime and connection events.

All data comes from the ace_stat MongoDB on the controller via the read-only
ace-stat-api sidecar (ACE_STAT_URL). No writes are performed.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from ..utils import get_logger

_RANGES = ("5minutes", "hourly", "daily", "monthly")

logger = get_logger(__name__)


def _client(settings: Settings) -> httpx.AsyncClient:
    if not settings.ace_stat_url:
        raise RuntimeError(
            "ace_stat analytics are not configured (ACE_STAT_URL is unset). "
            "The ace-stat-api sidecar must be running on the controller."
        )
    return httpx.AsyncClient(base_url=settings.ace_stat_url.rstrip("/"), timeout=60.0)


async def _get(settings: Settings, path: str, **params: Any) -> Any:
    async with _client(settings) as client:
        resp = await client.get(path, params={k: v for k, v in params.items() if v is not None})
        if resp.status_code != 200:
            raise RuntimeError(f"ace-stat-api error {resp.status_code}: {resp.text[:300]}")
        return resp.json()


async def get_ace_stat_health(settings: Settings) -> dict[str, Any]:
    """Get ace_stat analytics bridge status.

    Returns collection document counts, the most recent 5-minute sample time,
    and the size of the DPI app/category name catalog loaded by the sidecar.

    Args:
        settings: Application settings

    Returns:
        Health/status dictionary for the ace_stat bridge.
    """
    return await _get(settings, "/health")


async def get_dpi_analytics(
    settings: Settings,
    time_range: str = "hourly",
    hours: int | None = None,
) -> dict[str, Any]:
    """Get DPI (deep packet inspection) application, category and country analytics.

    Aggregates byte counters from the controller's ace_stat database. This is the
    deep historical app-level data (per-app and per-category bytes, plus
    per-country traffic) that the legacy API's stat/dpi endpoint does not expose.

    Args:
        settings: Application settings
        time_range: Aggregation bucket granularity: '5minutes', 'hourly',
            'daily', or 'monthly'. Default 'hourly'.
        hours: Optional lookback window in hours (e.g. 24 for last day).
            Omit for the full retention of the selected granularity.

    Returns:
        Dict with total/unidentified bytes, top applications (named),
        category roll-ups (named), and per-country byte counters.
    """
    if time_range not in _RANGES:
        raise ValueError(f"time_range must be one of {_RANGES}, got '{time_range}'")
    return await _get(settings, "/dpi", range=time_range, hours=hours)


async def get_wan_health_history(
    settings: Settings,
    time_range: str = "hourly",
    hours: int | None = None,
) -> list[dict[str, Any]]:
    """Get WAN/LAN health history for the gateway.

    Returns per-bucket latency (avg/max), WAN availability, rx/tx bytes,
    dropped packets, ISP name/ASN, and gateway CPU/memory from ace_stat.

    Args:
        settings: Application settings
        time_range: Bucket granularity: '5minutes', 'hourly', 'daily', 'monthly'.
        hours: Optional lookback window in hours.

    Returns:
        List of gateway health samples ordered by time (oldest first).
    """
    if time_range not in _RANGES:
        raise ValueError(f"time_range must be one of {_RANGES}, got '{time_range}'")
    return await _get(settings, "/wan", range=time_range, hours=hours)


async def get_client_wifi_quality(
    settings: Settings,
    time_range: str = "5minutes",
    hours: int | None = None,
) -> list[dict[str, Any]]:
    """Get per-client WiFi quality samples from ace_stat.

    Returns per-bucket rx/tx bytes, RSSI, signal, satisfaction, tx retries and
    WiFi tx drops for client sessions, ordered by time.

    Args:
        settings: Application settings
        time_range: Bucket granularity: '5minutes', 'hourly', 'daily', 'monthly'.
        hours: Optional lookback window in hours.

    Returns:
        List of client WiFi quality samples (oldest first).
    """
    if time_range not in _RANGES:
        raise ValueError(f"time_range must be one of {_RANGES}, got '{time_range}'")
    return await _get(settings, "/wifi/clients", range=time_range, hours=hours)


async def get_downtime_events(settings: Settings) -> list[dict[str, Any]]:
    """Get WAN downtime events from ace_stat.

    Returns recorded WAN outages with timestamps and duration in milliseconds.

    Args:
        settings: Application settings

    Returns:
        List of downtime event dicts (site_id, wan, timestamp, downtime_ms).
    """
    return await _get(settings, "/downtime")


async def get_wifi_connection_events(
    settings: Settings,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get recent WiFi connection events from ace_stat.

    Returns client connect/disconnect events with per-stage timing deltas
    (association, WPA authentication, DHCP, traffic).

    Args:
        settings: Application settings
        limit: Maximum number of events to return (1-500, default 50).

    Returns:
        List of connection events (most recent first).
    """
    return await _get(settings, "/connection_events", limit=limit)
