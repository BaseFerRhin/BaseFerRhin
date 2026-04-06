"""Persist Site aggregates to SQLite via sqlite-utils."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlite_utils import Database

from src.domain.models import Site

logger = logging.getLogger(__name__)

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sites (
  site_id TEXT PRIMARY KEY,
  nom_site TEXT NOT NULL,
  variantes_nom TEXT NOT NULL,
  pays TEXT NOT NULL,
  region_admin TEXT NOT NULL,
  commune TEXT NOT NULL,
  latitude REAL,
  longitude REAL,
  precision_localisation TEXT NOT NULL,
  type_site TEXT NOT NULL,
  description TEXT,
  surface_m2 REAL,
  altitude_m REAL,
  statut_fouille TEXT,
  identifiants_externes TEXT NOT NULL,
  commentaire_qualite TEXT,
  date_creation TEXT NOT NULL,
  date_maj TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sites_site_id ON sites(site_id);
CREATE INDEX IF NOT EXISTS ix_sites_commune ON sites(commune);
CREATE INDEX IF NOT EXISTS ix_sites_type_site ON sites(type_site);
CREATE TABLE IF NOT EXISTS phases (
  phase_id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
  periode TEXT NOT NULL,
  sous_periode TEXT,
  datation_debut INTEGER,
  datation_fin INTEGER,
  methode_datation TEXT,
  mobilier_associe TEXT NOT NULL,
  date_creation TEXT NOT NULL,
  date_maj TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
  reference TEXT NOT NULL,
  type_source TEXT,
  url TEXT,
  ark_gallica TEXT,
  page_gallica INTEGER,
  niveau_confiance TEXT NOT NULL,
  confiance_ocr REAL,
  date_extraction TEXT NOT NULL
);
"""


class SQLiteRepository:
    def save(self, sites: list[Site], db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = Database(db_path, recreate=True)
        db.executescript(_SCHEMA)
        db.execute("PRAGMA foreign_keys = ON")
        site_rows: list[dict[str, Any]] = []
        phase_rows: list[dict[str, Any]] = []
        source_rows: list[dict[str, Any]] = []
        for site in sites:
            d = site.model_dump(mode="json")
            phases = d.pop("phases")
            sources = d.pop("sources")
            d["variantes_nom"] = json.dumps(d["variantes_nom"])
            d["identifiants_externes"] = json.dumps(d["identifiants_externes"])
            site_rows.append(d)
            for ph in phases:
                pr = dict(ph)
                pr["mobilier_associe"] = json.dumps(pr["mobilier_associe"])
                phase_rows.append(pr)
            for src in sources:
                source_rows.append(dict(src))
        if site_rows:
            db["sites"].insert_all(site_rows, pk="site_id", replace=True)
        if phase_rows:
            db["phases"].insert_all(phase_rows, pk="phase_id", replace=True)
        if source_rows:
            db["sources"].insert_all(source_rows, pk="source_id", replace=True)
        logger.info("saved %d sites, %d phases, %d sources to %s", len(site_rows), len(phase_rows), len(source_rows), db_path)
