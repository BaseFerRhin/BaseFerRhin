"""Geocoding protocol and shared result type (EPSG:2154 Lambert-93)."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pyproj import Transformer

_WGS84_TO_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


def wgs84_to_l93(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 (lon, lat) to Lambert-93 (x, y)."""
    return _WGS84_TO_L93.transform(lon, lat)


@dataclass
class GeoResult:
    """Single geocoding hit in Lambert-93 (EPSG:2154)."""

    x_l93: float
    y_l93: float
    precision: str  # "exact" | "approx" | "centroide"
    source_api: str
    raw_response: dict[str, Any]


@runtime_checkable
class Geocoder(Protocol):
    """Resolves a commune (and optional site) to Lambert-93 coordinates."""

    def geocode(self, commune: str, site_name: str | None, pays: str) -> GeoResult | None:
        """Return coordinates or ``None`` if lookup fails."""
        ...
