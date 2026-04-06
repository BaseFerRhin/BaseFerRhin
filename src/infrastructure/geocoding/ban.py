"""French municipality geocoding via Base Adresse Nationale API."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx

from .base import GeoResult, wgs84_to_l93

logger = logging.getLogger(__name__)

_BAN_URL = "https://api-adresse.data.gouv.fr/search/"


class BANGeocoder:
    """BAN ``type=municipality`` search (commune centroid), returns Lambert-93."""

    def geocode(self, commune: str, site_name: str | None, pays: str) -> GeoResult | None:
        _ = site_name, pays
        q = quote_plus(commune.strip())
        url = f"{_BAN_URL}?q={q}&type=municipality&limit=1"
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(url)
                r.raise_for_status()
                data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("BAN request failed for %r: %s", commune, e)
            return None
        feats = data.get("features") or []
        if not feats:
            return None
        geom = feats[0].get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords or len(coords) < 2:
            return None
        lon, lat = float(coords[0]), float(coords[1])
        x, y = wgs84_to_l93(lon, lat)
        return GeoResult(
            x_l93=x,
            y_l93=y,
            precision="centroide",
            source_api="ban",
            raw_response={"feature": feats[0], "collection": data},
        )
