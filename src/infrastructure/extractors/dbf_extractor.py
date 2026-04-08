"""DBF file extractor via dbfread (ea_fr.dbf, afeaf_lineaire.dbf, etc.)."""

from __future__ import annotations

import logging
from pathlib import Path

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)


class DBFExtractor:
    """Extract records from dBASE .dbf files."""

    def __init__(
        self,
        *,
        encoding: str = "latin-1",
        column_mapping: dict[str, str] | None = None,
    ) -> None:
        self._encoding = encoding
        self._column_mapping = column_mapping or {}

    def supported_formats(self) -> list[str]:
        return [".dbf"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        from dbfread import DBF

        db = DBF(str(source_path), encoding=self._encoding)
        records: list[RawRecord] = []

        for rec in db:
            row = dict(rec)
            records.append(self._row_to_record(row, str(source_path.resolve())))

        logger.info("DBF %s: %d records extracted", source_path.name, len(records))
        return records

    def _row_to_record(self, row: dict, path_str: str) -> RawRecord:
        commune = self._get_mapped(row, "commune")
        type_mention = self._get_mapped(row, "type_mention")
        periode_mention = self._get_mapped(row, "periode_mention")
        lat = self._to_float(self._get_mapped(row, "latitude_raw"))
        lon = self._to_float(self._get_mapped(row, "longitude_raw"))

        extra = {}
        for key, val in row.items():
            mapped = self._column_mapping.get(key, key)
            if mapped not in ("commune", "type_mention", "periode_mention", "latitude_raw", "longitude_raw"):
                extra[key] = val

        raw_text = " | ".join(f"{k}={v}" for k, v in row.items() if v not in (None, ""))

        return RawRecord(
            raw_text=raw_text,
            commune=commune or None,
            type_mention=type_mention or None,
            periode_mention=periode_mention or None,
            latitude_raw=lat,
            longitude_raw=lon,
            source_path=path_str,
            extraction_method="dbf",
            extra=extra,
        )

    def _get_mapped(self, row: dict, target: str) -> str | None:
        for src_col, tgt in self._column_mapping.items():
            if tgt == target and src_col in row:
                val = row[src_col]
                return str(val).strip() if val is not None else None
        return None

    @staticmethod
    def _to_float(val: str | None) -> float | None:
        if not val:
            return None
        try:
            return float(val.replace(",", "."))
        except (ValueError, AttributeError):
            return None
