"""Export sites with coordinates to GeoJSON via GeoPandas."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

from src.domain.models import Site

logger = logging.getLogger(__name__)


class GeoJSONExporter:
    def export(self, sites: list[Site], output_path: Path) -> None:
        rows: list[dict[str, Any]] = []
        for s in sites:
            if s.latitude is None or s.longitude is None:
                continue
            periodes = ", ".join(p.periode.value for p in s.phases) if s.phases else ""
            d = s.model_dump(mode="json")
            d.pop("phases", None)
            d.pop("sources", None)
            d["periodes"] = periodes
            d["geometry"] = Point(float(s.longitude), float(s.latitude))
            rows.append(d)
        if not rows:
            logger.warning("no sites with coordinates; skipping %s", output_path)
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
        gdf.to_file(output_path, driver="GeoJSON")
        logger.info("wrote %d features to %s", len(gdf), output_path)
