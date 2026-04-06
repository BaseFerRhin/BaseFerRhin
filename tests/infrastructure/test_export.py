"""Tests for SQLite persistence and GeoJSON/CSV export."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlite_utils import Database

from src.domain.models import (
    Pays,
    Periode,
    PhaseOccupation,
    PrecisionLocalisation,
    Site,
    Source,
    TypeSite,
)
from src.infrastructure.persistence import CSVExporter, GeoJSONExporter, SQLiteRepository


def _minimal_site(
    site_id: str,
    *,
    lat: float | None = 48.0,
    lon: float | None = 7.5,
    phases: list[PhaseOccupation] | None = None,
) -> Site:
    return Site(
        site_id=site_id,
        nom_site=f"Site {site_id}",
        variantes_nom=[],
        pays=Pays.FR,
        region_admin="Grand Est",
        commune="Testville",
        latitude=lat,
        longitude=lon,
        precision_localisation=PrecisionLocalisation.EXACT,
        type_site=TypeSite.HABITAT,
        phases=phases or [],
        sources=[
            Source(
                source_id=f"{site_id}-src",
                site_id=site_id,
                reference=f"Ref {site_id}",
                date_extraction=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ],
        date_creation=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_maj=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def test_sqlite_fk_integrity(tmp_path: Path):
    repo = SQLiteRepository()
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    sites = [
        _minimal_site(
            "fk-s1",
            phases=[
                PhaseOccupation(
                    phase_id="fk-s1-p1",
                    site_id="fk-s1",
                    periode=Periode.HALLSTATT,
                    sous_periode="Ha D",
                    date_creation=ts,
                    date_maj=ts,
                )
            ],
        ),
        _minimal_site(
            "fk-s2",
            phases=[
                PhaseOccupation(
                    phase_id="fk-s2-p1",
                    site_id="fk-s2",
                    periode=Periode.LA_TENE,
                    sous_periode="LT C",
                    date_creation=ts,
                    date_maj=ts,
                )
            ],
        ),
        _minimal_site("fk-s3"),
    ]
    db_path = tmp_path / "test.db"
    repo.save(sites, db_path)
    db = Database(db_path)
    violations = list(db.execute("PRAGMA foreign_key_check"))
    assert violations == []


def test_geojson_valid(tmp_path: Path):
    out = tmp_path / "out.geojson"
    sites = [
        _minimal_site("g1", lat=48.08, lon=7.36),
        _minimal_site("g2", lat=47.56, lon=7.59),
    ]
    GeoJSONExporter().export(sites, out)
    text = out.read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["type"] in ("FeatureCollection",)
    assert "features" in data
    assert len(data["features"]) == 2
    for feat in data["features"]:
        assert feat["type"] == "Feature"
        assert "geometry" in feat
        assert feat["geometry"]["type"] == "Point"
        assert len(feat["geometry"]["coordinates"]) == 2
        assert "properties" in feat


def test_csv_multi_phase_rows(tmp_path: Path):
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    site = _minimal_site(
        "multi-ph",
        phases=[
            PhaseOccupation(
                phase_id="multi-ph-p1",
                site_id="multi-ph",
                periode=Periode.HALLSTATT,
                sous_periode="Ha D",
                date_creation=ts,
                date_maj=ts,
            ),
            PhaseOccupation(
                phase_id="multi-ph-p2",
                site_id="multi-ph",
                periode=Periode.LA_TENE,
                sous_periode="LT C",
                date_creation=ts,
                date_maj=ts,
            ),
        ],
    )
    out = tmp_path / "out.csv"
    CSVExporter().export([site], out)
    with out.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    phase_ids = {r["phase_id"] for r in rows}
    assert phase_ids == {"multi-ph-p1", "multi-ph-p2"}


def test_sites_without_coords_excluded_from_geojson(tmp_path: Path):
    out = tmp_path / "partial.geojson"
    with_coords = _minimal_site("with-g", lat=48.5, lon=7.6)
    without = _minimal_site("no-g", lat=None, lon=None)
    GeoJSONExporter().export([with_coords, without], out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["site_id"] == "with-g"
