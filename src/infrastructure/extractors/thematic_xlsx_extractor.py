"""Thematic XLSX extractors for BdD Proto, Nécropoles, Inhumations, Habitats-tombes riches."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)

_IRON_AGE_COLS = ("BF3_HaC", "HaD", "LTAB", "LTCD")
_C14_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)(?:\s*(?:avant|av\.?)\s*(?:J\.?-?C\.?)?)?", re.IGNORECASE)
_PARASITIC_RE = re.compile(r"(?i)TOTAL|Supprimé|Département|^$")
_PARASITIC_DEPT_RE = re.compile(r"(?i)Manque|Total|^$|^\s*$")

_PAYS_MAP = {"f": "FR", "fr": "FR", "d": "DE", "de": "DE", "ch": "CH", "s": "CH"}
_RICH_TYPE_MAP = {
    "tombe princière": "nécropole",
    "tombe princière ?": "nécropole",
    "tombe": "nécropole",
    "tombe à char": "nécropole",
    "nécropole": "nécropole",
    "habitat": "habitat",
    "habitat de hauteur": "habitat",
    "habitat fortifié": "oppidum",
    "site fortifié de hauteur": "oppidum",
    "site fortifié": "oppidum",
    "oppidum": "oppidum",
    "dépôt": "dépôt",
    "tumulus": "tumulus",
}


class BdDProtoAlsaceExtractor:
    """BdD Proto Alsace — filter Bronze-only, retain Iron Age rows."""

    def supported_formats(self) -> list[str]:
        return [".xlsx"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        df = pd.read_excel(source_path, engine="openpyxl")
        records: list[RawRecord] = []
        excluded = 0

        for _, row in df.iterrows():
            if not self._has_iron_age(row):
                excluded += 1
                continue
            records.append(self._to_record(row, str(source_path.resolve())))

        logger.info("BdD Proto Alsace: %d records, %d Bronze-only excluded", len(records), excluded)
        return records

    @staticmethod
    def _has_iron_age(row) -> bool:
        return any(
            row.get(col) is not None
            and not (isinstance(row.get(col), float) and pd.isna(row.get(col)))
            and row.get(col) not in (0, 0.0, "", "0")
            for col in _IRON_AGE_COLS
        )

    def _to_record(self, row, path_str: str) -> RawRecord:
        phases = [col for col in _IRON_AGE_COLS if row.get(col) and not (isinstance(row.get(col), float) and pd.isna(row.get(col))) and row.get(col) not in (0, 0.0)]
        commune = str(row.get("commune") or "").strip()
        lieu_dit = str(row.get("lieu_dit") or "").strip()
        type_site = str(row.get("type_site") or "").strip()
        datation = str(row.get("datation_1") or "").strip()

        extra = {
            "phases_bool": phases,
            "EA": str(row.get("EA") or "").strip() or None,
            "type_precision": str(row.get("type_precision") or "").strip() or None,
        }
        if lieu_dit:
            extra["lieu_dit"] = lieu_dit

        return RawRecord(
            raw_text=f"{commune} {lieu_dit} {type_site}",
            commune=commune or None,
            type_mention=type_site or "indéterminé",
            periode_mention=datation or None,
            latitude_raw=None,
            longitude_raw=None,
            source_path=path_str,
            extraction_method="bdd_proto_alsace",
            extra=extra,
        )


class NecropoleExtractor:
    """Nécropoles BFIIIb-HaD3 Alsace-Lorraine with optional department filtering."""

    def __init__(self, *, filter_departments: list[int] | None = None) -> None:
        self._filter_depts = set(filter_departments) if filter_departments else None

    def supported_formats(self) -> list[str]:
        return [".xlsx"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        df = pd.read_excel(source_path, engine="openpyxl")
        records: list[RawRecord] = []
        excluded = 0

        for _, row in df.iterrows():
            dept = row.get("Dept")
            if self._filter_depts:
                try:
                    dept_int = int(dept)
                except (TypeError, ValueError):
                    excluded += 1
                    continue
                if dept_int not in self._filter_depts:
                    excluded += 1
                    continue

            commune = str(row.get("Commune") or "").strip()
            nom = str(row.get("Nom") or "").strip()
            datation = str(row.get("Datation") or "").strip()
            x = self._to_float(row.get("Coordonnées x (Lambert 93)"))
            y = self._to_float(row.get("Coordonnées y (Lambert 93)"))

            extra = {"lieu_dit": nom} if nom else {}
            if x and y:
                extra["x_l93"] = x
                extra["y_l93"] = y
                extra["epsg_source"] = 2154

            records.append(RawRecord(
                raw_text=f"{commune} {nom} {datation}",
                commune=commune or None,
                type_mention="nécropole",
                periode_mention=datation or None,
                latitude_raw=None,
                longitude_raw=None,
                source_path=str(source_path.resolve()),
                extraction_method="necropoles",
                extra=extra,
            ))

        if excluded:
            logger.info("Nécropoles: %d excluded by dept filter", excluded)
        logger.info("Nécropoles: %d records", len(records))
        return records

    @staticmethod
    def _to_float(val) -> float | None:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None


class InhumationsSilosExtractor:
    """Aggregate individual-level Inhumations silos rows to site-level records."""

    def __init__(self, *, filter_departments: list[int] | None = None) -> None:
        self._filter_depts = set(filter_departments) if filter_departments else None

    def supported_formats(self) -> list[str]:
        return [".xlsx"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        df = pd.read_excel(source_path, engine="openpyxl")
        sites: dict[str, dict] = defaultdict(lambda: {
            "count": 0, "x": None, "y": None, "dept": None, "lieu_dit": None,
            "c14_values": [],
        })

        excluded = 0
        for _, row in df.iterrows():
            dept = str(row.get("Département") or "").strip()
            if _PARASITIC_RE.match(dept):
                excluded += 1
                continue

            if self._filter_depts:
                try:
                    dept_int = int(dept)
                    if dept_int not in self._filter_depts:
                        excluded += 1
                        continue
                except (ValueError, TypeError):
                    pass

            commune_val = row.get("Site") or row.get("Commune") or ""
            commune = str(commune_val).strip()
            lieu_dit_val = row.get("Lieu dit") or row.get("Lieu-dit") or ""
            lieu_dit = str(lieu_dit_val).strip()
            key = f"{commune}|{lieu_dit}"

            site = sites[key]
            site["count"] += 1
            site["commune"] = commune
            site["dept"] = dept
            if lieu_dit:
                site["lieu_dit"] = lieu_dit

            x = self._to_float(row.get("X(L93)") or row.get("X_L93"))
            y = self._to_float(row.get("Y(L93)") or row.get("Y_L93"))
            if x and y and site["x"] is None:
                site["x"] = x
                site["y"] = y

            c14 = str(row.get("14C (2 sigma)") or row.get("C14") or "").strip()
            if c14:
                site["c14_values"].append(c14)

        records: list[RawRecord] = []
        for key, site in sites.items():
            extra: dict = {
                "individus_count": site["count"],
            }
            if site["lieu_dit"]:
                extra["lieu_dit"] = site["lieu_dit"]
            if site["x"] and site["y"]:
                extra["x_l93"] = site["x"]
                extra["y_l93"] = site["y"]
                extra["epsg_source"] = 2154

            c14_dates = self._parse_c14_list(site["c14_values"])
            if c14_dates:
                extra["datation_14c_debut"] = min(d for d, _ in c14_dates)
                extra["datation_14c_fin"] = max(f for _, f in c14_dates)

            records.append(RawRecord(
                raw_text=f"{site['commune']} {site.get('lieu_dit', '')} ({site['count']} individus)",
                commune=site["commune"] or None,
                type_mention="nécropole",
                periode_mention=None,
                latitude_raw=None,
                longitude_raw=None,
                source_path=str(source_path.resolve()),
                extraction_method="inhumations_silos",
                extra=extra,
            ))

        if excluded:
            logger.info("Inhumations silos: %d parasitic rows excluded", excluded)
        logger.info("Inhumations silos: %d → %d sites", sum(s["count"] for s in sites.values()), len(records))
        return records

    @staticmethod
    def _to_float(val) -> float | None:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            return float(str(val).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_c14_list(values: list[str]) -> list[tuple[int, int]]:
        results = []
        for v in values:
            m = _C14_RE.search(v)
            if m:
                results.append((-int(m.group(1)), -int(m.group(2))))
        return results


class HabitatsTombesRichesExtractor:
    """Habitats-tombes riches Alsace-Lorraine with pays/type normalization."""

    def __init__(self, *, filter_departments: list[int] | None = None) -> None:
        self._filter_depts = set(filter_departments) if filter_departments else None

    def supported_formats(self) -> list[str]:
        return [".xlsx"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        df = pd.read_excel(source_path, engine="openpyxl")
        records: list[RawRecord] = []
        excluded = 0

        for _, row in df.iterrows():
            dept_land = str(row.get("Dept/Land") or "").strip()
            if _PARASITIC_DEPT_RE.match(dept_land):
                excluded += 1
                continue

            if self._filter_depts:
                try:
                    dept_int = int(dept_land)
                    if dept_int not in self._filter_depts:
                        excluded += 1
                        continue
                except (ValueError, TypeError):
                    pass

            pays_raw = str(row.get("Pays") or "").strip().lower()
            pays = _PAYS_MAP.get(pays_raw, pays_raw.upper())

            commune = str(row.get("Commune") or "").strip()
            lieu_dit = str(row.get("Lieudit") or "").strip()
            type_raw = str(row.get("type") or "").strip().lower()
            type_mention = _RICH_TYPE_MAP.get(type_raw, "indéterminé")

            extra: dict = {"pays": pays, "dept_land": dept_land}
            if lieu_dit:
                extra["lieu_dit"] = lieu_dit

            records.append(RawRecord(
                raw_text=f"{pays} {commune} {lieu_dit} {type_raw}",
                commune=commune or None,
                type_mention=type_mention,
                periode_mention=None,
                latitude_raw=None,
                longitude_raw=None,
                source_path=str(source_path.resolve()),
                extraction_method="habitats_tombes_riches",
                extra=extra,
            ))

        if excluded:
            logger.info("Habitats-tombes riches: %d parasitic rows excluded", excluded)
        logger.info("Habitats-tombes riches: %d records", len(records))
        return records

    @staticmethod
    def _to_float(val) -> float | None:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
