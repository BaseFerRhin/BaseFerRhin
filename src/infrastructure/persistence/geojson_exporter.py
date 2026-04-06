"""Export sites with coordinates to GeoJSON via GeoPandas (L93 → WGS84)."""

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
            if s.x_l93 is None or s.y_l93 is None:
                continue
            periodes = ", ".join(p.periode.value for p in s.phases) if s.phases else ""
            d = s.model_dump(mode="json")
            d.pop("phases", None)
            d.pop("sources", None)
            d["periodes"] = periodes
            d["geometry"] = Point(float(s.x_l93), float(s.y_l93))
            rows.append(d)
        if not rows:
            logger.warning("no sites with coordinates; skipping %s", output_path)
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:2154")
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        gdf_wgs84.to_file(output_path, driver="GeoJSON")
        logger.info("wrote %d features to %s (reprojected to WGS84)", len(gdf_wgs84), output_path)
