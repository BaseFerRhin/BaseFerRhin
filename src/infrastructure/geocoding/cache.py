"""JSON file cache for geocoding results."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import GeoResult

logger = logging.getLogger(__name__)


def _key(commune: str, pays: str) -> str:
    return f"{pays.strip().upper()}::{commune.strip().casefold()}"


def _result_to_dict(r: GeoResult) -> dict[str, Any]:
    return {
        "latitude": r.latitude,
        "longitude": r.longitude,
        "precision": r.precision,
        "source_api": r.source_api,
        "raw_response": r.raw_response,
    }


def _dict_to_result(d: dict[str, Any]) -> GeoResult:
    return GeoResult(
        latitude=float(d["latitude"]),
        longitude=float(d["longitude"]),
        precision=str(d["precision"]),
        source_api=str(d["source_api"]),
        raw_response=dict(d.get("raw_response") or {}),
    )


class GeocodingCache:
    """Persistent key-value cache: (commune, pays) → ``GeoResult``."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    def get(self, commune: str, pays: str) -> GeoResult | None:
        entry = self._data.get(_key(commune, pays))
        if not entry:
            return None
        try:
            return _dict_to_result(entry)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("bad cache entry for %s: %s", _key(commune, pays), e)
            return None

    def put(self, commune: str, pays: str, result: GeoResult) -> None:
        self._data[_key(commune, pays)] = _result_to_dict(result)

    def load(self, path: Path) -> None:
        if not path.is_file():
            self._data = {}
            return
        raw = path.read_text(encoding="utf-8")
        self._data = json.loads(raw) if raw.strip() else {}
        logger.info("geocoding cache loaded: %d keys from %s", len(self._data), path)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("geocoding cache saved: %d keys to %s", len(self._data), path)
