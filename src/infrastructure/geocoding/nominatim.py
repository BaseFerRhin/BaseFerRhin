"""OpenStreetMap Nominatim via geopy with polite rate limiting."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from geopy.geocoders import Nominatim

from .base import GeoResult, wgs84_to_l93

logger = logging.getLogger(__name__)

_USER_AGENT = "baseferrhin"
_MIN_INTERVAL = 1.0


class NominatimGeocoder:
    """Nominatim with ``countrycodes`` filter and ~1 request/second throttle."""

    def __init__(self, countrycodes: str | None = None) -> None:
        self._countrycodes = countrycodes
        self._locator = Nominatim(user_agent=_USER_AGENT)
        self._last_call: float = 0.0

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = max(0.0, _MIN_INTERVAL - (now - self._last_call))
        if wait <= 0:
            self._last_call = now
            return

        async def _sleep(seconds: float) -> None:
            await asyncio.sleep(seconds)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_sleep(wait))
        else:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def geocode(self, commune: str, site_name: str | None, pays: str) -> GeoResult | None:
        _ = pays
        parts = [p for p in (site_name, commune) if p and str(p).strip()]
        query = ", ".join(parts) if parts else commune.strip()
        if not query:
            return None
        self._throttle()
        opts: dict[str, Any] = {"exactly_one": True, "language": "fr"}
        if self._countrycodes:
            opts["country_codes"] = self._countrycodes
        try:
            loc = self._locator.geocode(query, **opts)
        except Exception as e:
            logger.warning("Nominatim failed for %r: %s", query, e)
            return None
        if loc is None:
            return None
        raw: dict[str, Any] = getattr(loc, "raw", {}) or {}
        prec = "approx"
        if raw.get("addresstype") == "municipality" or raw.get("type") in ("administrative",):
            prec = "centroide"
        x, y = wgs84_to_l93(float(loc.longitude), float(loc.latitude))
        return GeoResult(
            x_l93=x,
            y_l93=y,
            precision=prec,
            source_api="nominatim",
            raw_response=raw if isinstance(raw, dict) else {"raw": raw},
        )
