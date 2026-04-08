"""Convert BaseFerRhin pipeline data (VALIDATE.json) into a DuckDB database.

Usage:
    python src/keplergl/scripts/build_duckdb.py

Reads: data/processed/VALIDATE.json  (or EXPORT.json as fallback)
Writes: src/keplergl/data/sites.duckdb
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
from pyproj import Transformer

_L93_TO_WGS = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DB = PROJECT_ROOT / "src" / "keplergl" / "data" / "sites.duckdb"


def load_pipeline_state() -> dict:
    for name in ("EXPORT.json", "VALIDATE.json", "GEOCODE.json"):
        path = PROCESSED_DIR / name
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("state", {}).get("sites"):
                print(f"✓ Chargement depuis {path.name} ({len(data['state']['sites'])} sites)")
                return data["state"]
    sys.exit("Aucun fichier pipeline trouvé avec des sites.")


def build_database(state: dict) -> None:
    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    db = duckdb.connect(str(OUTPUT_DB))

    db.execute("""
        CREATE TABLE sites (
            site_id          VARCHAR PRIMARY KEY,
            nom_site         VARCHAR NOT NULL,
            variantes_nom    VARCHAR[],
            pays             VARCHAR NOT NULL,
            region_admin     VARCHAR NOT NULL,
            commune          VARCHAR NOT NULL,
            x_l93            DOUBLE,
            y_l93            DOUBLE,
            latitude         DOUBLE,
            longitude        DOUBLE,
            precision_loc    VARCHAR,
            type_site        VARCHAR NOT NULL,
            description      VARCHAR,
            surface_m2       DOUBLE,
            altitude_m       DOUBLE,
            statut_fouille   VARCHAR,
            commentaire_qual VARCHAR,
            date_creation    TIMESTAMP,
            date_maj         TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE phases (
            phase_id         VARCHAR PRIMARY KEY,
            site_id          VARCHAR NOT NULL REFERENCES sites(site_id),
            periode          VARCHAR NOT NULL,
            sous_periode     VARCHAR,
            datation_debut   INTEGER,
            datation_fin     INTEGER,
            methode_datation VARCHAR,
            date_creation    TIMESTAMP,
            date_maj         TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE sources (
            source_id        VARCHAR PRIMARY KEY,
            site_id          VARCHAR NOT NULL REFERENCES sites(site_id),
            reference        VARCHAR,
            type_source      VARCHAR,
            url              VARCHAR,
            ark_gallica      VARCHAR,
            page_gallica     INTEGER,
            niveau_confiance VARCHAR,
            confiance_ocr    DOUBLE,
            date_extraction  TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE raw_records (
            id                 INTEGER PRIMARY KEY,
            raw_text           VARCHAR,
            commune            VARCHAR,
            type_mention       VARCHAR,
            periode_mention    VARCHAR,
            latitude_raw       DOUBLE,
            longitude_raw      DOUBLE,
            source_path        VARCHAR,
            page_number        INTEGER,
            extraction_method  VARCHAR,
            ark_id             VARCHAR,
            context_text       VARCHAR
        )
    """)

    # -- Insert sites --
    seen_sites: set[str] = set()
    for site in state["sites"]:
        if site["site_id"] in seen_sites:
            continue
        seen_sites.add(site["site_id"])

        x_l93 = site.get("x_l93")
        y_l93 = site.get("y_l93")
        lat, lon = None, None
        if x_l93 is not None and y_l93 is not None:
            lon, lat = _L93_TO_WGS.transform(x_l93, y_l93)

        db.execute(
            """INSERT INTO sites VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                site["site_id"],
                site["nom_site"],
                site.get("variantes_nom", []),
                site["pays"],
                site["region_admin"],
                site["commune"],
                x_l93,
                y_l93,
                lat,
                lon,
                site.get("precision_localisation"),
                site["type_site"],
                site.get("description"),
                site.get("surface_m2"),
                site.get("altitude_m"),
                site.get("statut_fouille"),
                site.get("commentaire_qualite"),
                site.get("date_creation"),
                site.get("date_maj"),
            ],
        )

        for phase in site.get("phases", []):
            db.execute(
                """INSERT OR IGNORE INTO phases VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    phase["phase_id"],
                    phase["site_id"],
                    phase["periode"],
                    phase.get("sous_periode"),
                    phase.get("datation_debut"),
                    phase.get("datation_fin"),
                    phase.get("methode_datation"),
                    phase.get("date_creation"),
                    phase.get("date_maj"),
                ],
            )

        for source in site.get("sources", []):
            db.execute(
                """INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?,?,?,?,?)""",
                [
                    source["source_id"],
                    source["site_id"],
                    source.get("reference"),
                    source.get("type_source"),
                    source.get("url"),
                    source.get("ark_gallica"),
                    source.get("page_gallica"),
                    source.get("niveau_confiance"),
                    source.get("confiance_ocr"),
                    source.get("date_extraction"),
                ],
            )

    # -- Insert raw_records --
    for i, rec in enumerate(state.get("raw_records", [])):
        db.execute(
            """INSERT INTO raw_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                i,
                rec.get("raw_text"),
                rec.get("commune"),
                rec.get("type_mention"),
                rec.get("periode_mention"),
                rec.get("latitude_raw"),
                rec.get("longitude_raw"),
                rec.get("source_path"),
                rec.get("page_number"),
                rec.get("extraction_method"),
                rec.get("ark_id"),
                rec.get("context_text"),
            ],
        )

    # -- Useful views --
    db.execute("""
        CREATE VIEW sites_with_phases AS
        SELECT
            s.site_id, s.nom_site, s.commune, s.pays, s.region_admin,
            s.x_l93, s.y_l93, s.precision_loc, s.type_site,
            s.description, s.surface_m2, s.altitude_m,
            p.phase_id, p.periode, p.sous_periode,
            p.datation_debut, p.datation_fin
        FROM sites s
        LEFT JOIN phases p ON s.site_id = p.site_id
    """)

    db.execute("""
        CREATE VIEW sites_geojson AS
        SELECT
            s.site_id, s.nom_site, s.commune, s.pays, s.region_admin,
            s.x_l93, s.y_l93, s.precision_loc, s.type_site,
            s.description, s.surface_m2, s.altitude_m,
            p.periode, p.sous_periode,
            (SELECT COUNT(*) FROM sources src WHERE src.site_id = s.site_id) AS sources_count
        FROM sites s
        LEFT JOIN phases p ON s.site_id = p.site_id
        WHERE s.x_l93 IS NOT NULL AND s.y_l93 IS NOT NULL
    """)

    counts = db.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
    phases_count = db.execute("SELECT COUNT(*) FROM phases").fetchone()[0]
    sources_count = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    raw_count = db.execute("SELECT COUNT(*) FROM raw_records").fetchone()[0]

    db.close()

    print(f"✓ Base DuckDB créée : {OUTPUT_DB}")
    print(f"  {counts} sites | {phases_count} phases | {sources_count} sources | {raw_count} raw_records")


def main():
    state = load_pipeline_state()
    build_database(state)


if __name__ == "__main__":
    main()
