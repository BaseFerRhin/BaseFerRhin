"""Load archaeological site data from pipeline output or test fixtures."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_SOURCES = [
    PROJECT_ROOT / "data" / "output" / "sites.geojson",
    PROJECT_ROOT / "tests" / "fixtures" / "golden_sites.json",
    PROJECT_ROOT / "data" / "sources" / "golden_sites.csv",
]


def load_sites() -> pd.DataFrame:
    """Try each data source in priority order and return a normalised DataFrame."""
    for path in _SOURCES:
        if not path.exists():
            continue
        logger.info("loading sites from %s", path)
        if path.suffix == ".geojson":
            return _from_geojson(path)
        if path.suffix == ".json":
            return _from_golden_json(path)
        if path.suffix == ".csv":
            return _from_golden_csv(path)
    raise FileNotFoundError("No site data found in any known location")


def _from_geojson(path: Path) -> pd.DataFrame:
    import geopandas as gpd

    gdf = gpd.read_file(path)
    if "geometry" in gdf.columns:
        gdf["latitude"] = gdf.geometry.y
        gdf["longitude"] = gdf.geometry.x
    df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore"))
    return df


def _from_golden_json(path: Path) -> pd.DataFrame:
    from pyproj import Transformer
    _l93_to_wgs = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

    raw: list[dict] = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for site in raw:
        periodes, sous_periodes = _extract_phases(site.get("phases", []))
        deb, fin = _extract_datation(site.get("phases", []))
        refs = [s.get("reference", "") for s in site.get("sources", [])]
        x, y = site.get("x_l93"), site.get("y_l93")
        lat, lon = (None, None)
        if x is not None and y is not None:
            lon, lat = _l93_to_wgs.transform(x, y)
        rows.append({
            "site_id": site["site_id"],
            "nom_site": site["nom_site"],
            "type_site": site["type_site"],
            "periodes": ", ".join(sorted(set(periodes))) if periodes else "indéterminé",
            "sous_periodes": ", ".join(sorted(set(sous_periodes))),
            "datation_debut": deb,
            "datation_fin": fin,
            "commune": site["commune"],
            "pays": site["pays"],
            "region_admin": site.get("region_admin", ""),
            "latitude": lat,
            "longitude": lon,
            "precision_localisation": site.get("precision_localisation", ""),
            "description": site.get("description", ""),
            "altitude_m": site.get("altitude_m"),
            "surface_m2": site.get("surface_m2"),
            "statut_fouille": site.get("statut_fouille", ""),
            "sources": "; ".join(refs),
        })
    logger.info("loaded %d sites from golden JSON", len(rows))
    return pd.DataFrame(rows)


def _from_golden_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df["nom_site"] = df["raw_text"].str.split(" — ").str[0]
    df = df.rename(columns={
        "type_mention": "type_site",
        "latitude_raw": "latitude",
        "longitude_raw": "longitude",
    })
    df["sous_periodes"] = df["periode_mention"].str.extract(r"((?:Ha|LT)\s*\w+)")
    df["periodes"] = df["periode_mention"].str.extract(r"(Hallstatt|La Tène|indéterminé)")
    df["periodes"] = df["periodes"].fillna("indéterminé")
    df["pays"] = "FR"
    df["region_admin"] = ""
    df["precision_localisation"] = ""
    df["description"] = df["raw_text"]
    logger.info("loaded %d sites from golden CSV", len(df))
    return df


def _extract_phases(phases: list[dict]) -> tuple[list[str], list[str]]:
    periodes = [ph["periode"] for ph in phases if ph.get("periode")]
    sous = [ph["sous_periode"] for ph in phases if ph.get("sous_periode")]
    return periodes, sous


def _extract_datation(phases: list[dict]) -> tuple[int | None, int | None]:
    debs = [ph["datation_debut"] for ph in phases if ph.get("datation_debut") is not None]
    fins = [ph["datation_fin"] for ph in phases if ph.get("datation_fin") is not None]
    return (min(debs) if debs else None, max(fins) if fins else None)
