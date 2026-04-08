"""Multi-EPSG coordinate reprojection to Lambert-93 (EPSG:2154)."""

from __future__ import annotations

import logging
import math
from typing import Optional

from pyproj import Transformer

logger = logging.getLogger(__name__)

_X_L93_MIN, _X_L93_MAX = 100_000.0, 1_200_000.0
_Y_L93_MIN, _Y_L93_MAX = 6_000_000.0, 7_200_000.0
_TARGET_EPSG = 2154


class Reprojector:
    """Reproject coordinates from any source EPSG to Lambert-93 with caching."""

    def __init__(self) -> None:
        self._transformers: dict[int, Transformer] = {}

    def _get_transformer(self, source_epsg: int) -> Transformer:
        if source_epsg not in self._transformers:
            self._transformers[source_epsg] = Transformer.from_crs(
                f"EPSG:{source_epsg}", f"EPSG:{_TARGET_EPSG}", always_xy=True
            )
        return self._transformers[source_epsg]

    def to_lambert93(
        self, x: float, y: float, source_epsg: int
    ) -> tuple[float, float, bool]:
        """Reproject (x, y) from source_epsg to Lambert-93.

        For WGS84 (4326): x=longitude, y=latitude.
        Returns (x_l93, y_l93, in_bounds).
        Raises ValueError for invalid inputs (NaN, inf, zero coords).
        """
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"Non-finite coordinates: ({x}, {y})")
        if x == 0.0 and y == 0.0:
            raise ValueError("Null Island coordinates (0, 0)")

        if source_epsg == _TARGET_EPSG:
            in_bounds = self._check_bounds(x, y)
            return x, y, in_bounds

        transformer = self._get_transformer(source_epsg)
        x_l93, y_l93 = transformer.transform(x, y)

        if not math.isfinite(x_l93) or not math.isfinite(y_l93):
            raise ValueError(
                f"Reprojection produced non-finite result: ({x}, {y}) EPSG:{source_epsg} → ({x_l93}, {y_l93})"
            )

        in_bounds = self._check_bounds(x_l93, y_l93)
        if not in_bounds:
            logger.warning(
                "Reprojected coords out of L93 bounds: (%s, %s) from EPSG:%d → (%s, %s)",
                x, y, source_epsg, x_l93, y_l93,
            )

        return x_l93, y_l93, in_bounds

    def to_lambert93_safe(
        self, x: Optional[float], y: Optional[float], source_epsg: Optional[int]
    ) -> tuple[Optional[float], Optional[float], bool]:
        """Null-safe version: returns (None, None, False) if inputs are invalid."""
        if x is None or y is None or source_epsg is None:
            return None, None, False
        try:
            return self.to_lambert93(x, y, source_epsg)
        except (ValueError, Exception) as exc:
            logger.warning("Reprojection failed for (%s, %s, EPSG:%s): %s", x, y, source_epsg, exc)
            return None, None, False

    @staticmethod
    def _check_bounds(x: float, y: float) -> bool:
        return _X_L93_MIN <= x <= _X_L93_MAX and _Y_L93_MIN <= y <= _Y_L93_MAX
