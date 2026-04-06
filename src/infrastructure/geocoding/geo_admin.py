"""Swiss locations search via api.geo.admin.ch SearchServer."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx

from .base import GeoResult, wgs84_to_l93

logger = logging.getLogger(__name__)

_GEOADMIN_URL = "https://api3.geo.admin.ch/rest/services/api/SearchServer"


class GeoAdminGeocoder:
    """Swiss SearchServer ``type=locations`` (commune / place)."""

    def geocode(self, commune: str, site_name: str | None, pays: str) -> GeoResult | None:
        _ = pays
        text = commune.strip()
        if site_name and str(site_name).strip():
            text = f"{site_name.strip()} {text}"
        q = quote_plus(text)
        url = f"{_GEOADMIN_URL}?searchText={q}&type=locations"
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(url)
                r.raise_for_status()
                data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("GeoAdmin request failed for %r: %s", text, e)
            return None
        results = data.get("results") or []
        if not results:
            return None
        attrs = results[0].get("attrs") or {}
        try:
            lat = float(attrs["lat"])
            lon = float(attrs["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        x, y = wgs84_to_l93(lon, lat)
        return GeoResult(
            x_l93=x,
            y_l93=y,
            precision="approx",
            source_api="geo_admin",
            raw_response={"result": results[0], "payload": data},
        )
