"""Geocoding protocol and shared result type."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class GeoResult:
    """Single geocoding hit with provenance."""

    latitude: float
    longitude: float
    precision: str  # "exact" | "approx" | "centroide"
    source_api: str
    raw_response: dict[str, Any]


@runtime_checkable
class Geocoder(Protocol):
    """Resolves a commune (and optional site) to coordinates."""

    def geocode(self, commune: str, site_name: str | None, pays: str) -> GeoResult | None:
        """Return coordinates or ``None`` if lookup fails."""
        ...
