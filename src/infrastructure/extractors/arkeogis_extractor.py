"""ArkeoGIS CSV export extractor (LoupBernard & ADAB variants)."""

from __future__ import annotations

import csv
import logging
import re
from io import StringIO
from pathlib import Path

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)

_ARKEOGIS_DATE_RE = re.compile(r"^(-?\d+):(-?\d+)$")
_COMMENT_FIELD_RE = re.compile(r"(\w+)\s*:\s*([^#]+?)(?:\s*#|$)")

_CARAC_TYPE_MAP: dict[str, str] = {
    "enceinte": "oppidum",
    "fortification": "oppidum",
    "funéraire": "nécropole",
    "habitat": "habitat",
    "groupé": "habitat",
    "dispersé": "habitat",
    "route/voie": "voie",
    "production": "atelier",
    "artisanat": "atelier",
    "cultuel": "sanctuaire",
    "dépôt": "dépôt",
}

_MATERIAL_TYPES = {"céramique", "métal", "lithique", "verre", "os", "terre cuite"}

_POST_ROMAN_CUTOFF = 500


class ArkeoGISExtractor:
    """Extract records from ArkeoGIS CSV exports."""

    def __init__(self, *, filter_age_du_fer: bool = False) -> None:
        self._filter_age_du_fer = filter_age_du_fer

    def supported_formats(self) -> list[str]:
        return [".csv"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        raw_bytes = source_path.read_bytes()
        text = self._decode(raw_bytes)
        reader = csv.DictReader(StringIO(text), delimiter=";")

        records: list[RawRecord] = []
        excluded = 0

        for row in reader:
            if self._filter_age_du_fer and self._should_exclude(row):
                excluded += 1
                continue
            records.append(self._row_to_record(row, str(source_path.resolve())))

        if excluded:
            logger.info(
                "ArkeoGIS %s: %d rows excluded by chronological filter",
                source_path.name, excluded,
            )
        logger.info("ArkeoGIS %s: %d records extracted", source_path.name, len(records))
        return records

    def _should_exclude(self, row: dict[str, str]) -> bool:
        sp = (row.get("STARTING_PERIOD") or "").strip()
        ep = (row.get("ENDING_PERIOD") or "").strip()

        if sp.lower() == "indéterminé" and (not ep or ep.lower() == "indéterminé"):
            return True
        if not sp and ep.lower() == "indéterminé":
            return True

        for period_str in (sp, ep):
            m = _ARKEOGIS_DATE_RE.match(period_str)
            if m:
                end_date = int(m.group(2))
                if end_date > _POST_ROMAN_CUTOFF:
                    return True
        return False

    def _row_to_record(self, row: dict[str, str], path_str: str) -> RawRecord:
        sp = (row.get("STARTING_PERIOD") or "").strip()
        ep = (row.get("ENDING_PERIOD") or "").strip()
        debut, fin = self._parse_date_range(sp, ep)

        carac = (row.get("CARAC_LVL1") or "").strip()
        type_mention = self._map_type(carac)

        centroid = (row.get("CITY_CENTROID") or "").strip()
        comments = row.get("COMMENTS") or ""
        precision = self._resolve_precision(centroid, comments)
        comment_fields = self._parse_comments(comments)

        lat = self._to_float(row.get("LATITUDE"))
        lon = self._to_float(row.get("LONGITUDE"))

        db_name = (row.get("DATABASE_NAME") or "").strip()
        pays = "DE" if any(kw in db_name.lower() for kw in ("bade", "baden", "adab", "nordbaden", "südbaden", "wurtemberg")) else ""

        extra: dict = {
            "SITE_AKG_ID": (row.get("SITE_AKG_ID") or "").strip(),
            "SITE_SOURCE_ID": (row.get("SITE_SOURCE_ID") or "").strip(),
            "DATABASE_NAME": db_name,
            "OCCUPATION": (row.get("OCCUPATION") or "").strip(),
            "CARAC_LVL1": carac,
            "precision_localisation": precision,
            "datation_debut": debut,
            "datation_fin": fin,
        }
        if pays:
            extra["pays"] = pays
        extra.update(comment_fields)

        commune = (row.get("MAIN_CITY_NAME") or "").strip()
        site_name = (row.get("SITE_NAME") or "").strip()

        raw_parts = [f"{k}={v}" for k, v in row.items() if v and v.strip()]
        raw_text = " | ".join(raw_parts)

        return RawRecord(
            raw_text=raw_text,
            commune=commune or site_name,
            type_mention=type_mention,
            periode_mention=f"{sp} / {ep}" if sp or ep else None,
            latitude_raw=lat,
            longitude_raw=lon,
            source_path=path_str,
            extraction_method="arkeogis",
            extra=extra,
        )

    def _parse_date_range(self, start: str, end: str) -> tuple[int | None, int | None]:
        debut: int | None = None
        fin: int | None = None

        m_start = _ARKEOGIS_DATE_RE.match(start)
        if m_start:
            debut = int(m_start.group(1))

        m_end = _ARKEOGIS_DATE_RE.match(end)
        if m_end:
            fin = int(m_end.group(2))
        elif m_start:
            fin = int(m_start.group(2))

        return debut, fin

    @staticmethod
    def _map_type(carac_lvl1: str) -> str:
        key = carac_lvl1.lower()
        if key in _MATERIAL_TYPES:
            return "indéterminé"
        return _CARAC_TYPE_MAP.get(key, "indéterminé")

    @staticmethod
    def _resolve_precision(centroid: str, comments: str) -> str:
        if centroid.lower() == "oui":
            return "centroïde"
        if "GENAUIGK_T" in comments:
            if "mit 20 m Toleranz" in comments or "ca. 10m" in comments:
                return "exact"
            if "Ungenauigkeit" in comments:
                return "approx"
        return "approx"

    @staticmethod
    def _parse_comments(comments: str) -> dict[str, str]:
        fields = {}
        for m in _COMMENT_FIELD_RE.finditer(comments):
            key, val = m.group(1).strip(), m.group(2).strip()
            if key in ("GENAUIGK_T", "DAT_FEIN", "TYP_FEIN", "TYP_GROB", "DAT_GROB", "LISTENTEXT"):
                if val and val != "--":
                    fields[key] = val
        return fields

    @staticmethod
    def _to_float(val: str | None) -> float | None:
        if not val:
            return None
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _decode(raw_bytes: bytes) -> str:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return raw_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode ArkeoGIS CSV")
