"""Country-aware geocoding with API fallbacks and JSON cache."""

from __future__ import annotations

import logging
from pathlib import Path

from .ban import BANGeocoder
from .base import GeoResult, Geocoder
from .cache import GeocodingCache
from .geo_admin import GeoAdminGeocoder
from .nominatim import NominatimGeocoder

logger = logging.getLogger(__name__)


class MultiGeocoder:
    """Dispatches by ``pays`` (FR / DE / CH) and caches successful lookups."""

    def __init__(self, cache: GeocodingCache | None = None, cache_path: Path | None = None) -> None:
        self._cache = cache or GeocodingCache()
        self._cache_path = cache_path
        if cache_path is not None:
            self._cache.load(cache_path)
        self._ban = BANGeocoder()
        self._geoadmin = GeoAdminGeocoder()
        self._nom_fr = NominatimGeocoder(countrycodes="fr")
        self._nom_de = NominatimGeocoder(countrycodes="de")
        self._nom_ch = NominatimGeocoder(countrycodes="ch")
        self._nom_fallback = NominatimGeocoder(countrycodes=None)

    def geocode(self, commune: str, site_name: str | None, pays: str) -> GeoResult | None:
        cc = pays.strip().upper()
        hit = self._cache.get(commune, cc)
        if hit is not None:
            return hit
        chain: list[Geocoder] = []
        if cc == "FR":
            chain = [self._ban, self._nom_fr]
        elif cc == "DE":
            chain = [self._nom_de]
        elif cc == "CH":
            chain = [self._geoadmin, self._nom_ch]
        else:
            logger.warning("unknown pays %r; trying Nominatim without country filter", pays)
            chain = [self._nom_fallback]

        result: GeoResult | None = None
        for g in chain:
            result = g.geocode(commune, site_name, cc)
            if result is not None:
                break
        if result is not None:
            self._cache.put(commune, cc, result)
            if self._cache_path is not None:
                self._cache.save(self._cache_path)
        return result
