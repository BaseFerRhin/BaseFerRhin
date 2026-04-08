"""ODS file extractor via pandas + odfpy (mobilier_sepult_def, etc.)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)


class ODSExtractor:
    """Extract records from ODS spreadsheets using pandas + odfpy engine."""

    def __init__(self, *, column_mapping: dict[str, str] | None = None) -> None:
        self._column_mapping = column_mapping or {
            "Commune": "commune",
            "chrono": "periode_mention",
            "type sép": "type_mention",
            "Coordonnées x (Lambert 93)": "x_l93",
            "Coordonnées y (Lambert 93)": "y_l93",
        }

    def supported_formats(self) -> list[str]:
        return [".ods"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        df = pd.read_excel(source_path, engine="odf")
        records: list[RawRecord] = []

        for _, row in df.iterrows():
            rec = self._row_to_record(row, df.columns, str(source_path.resolve()))
            if rec:
                records.append(rec)

        logger.info("ODS %s: %d records extracted", source_path.name, len(records))
        return records

    def _row_to_record(self, row, columns, path_str: str) -> RawRecord | None:
        commune = self._get_mapped(row, "commune")
        type_mention = self._get_mapped(row, "type_mention")
        periode = self._get_mapped(row, "periode_mention")

        x_l93 = self._to_float(self._get_mapped(row, "x_l93"))
        y_l93 = self._to_float(self._get_mapped(row, "y_l93"))

        if not commune and not x_l93:
            return None

        extra: dict = {}
        for col in columns:
            mapped = self._column_mapping.get(col, col)
            if mapped not in ("commune", "type_mention", "periode_mention", "x_l93", "y_l93"):
                val = row.get(col)
                if val is not None and not (isinstance(val, float) and pd.isna(val)):
                    extra[col] = val

        if x_l93 and y_l93:
            extra["x_l93"] = x_l93
            extra["y_l93"] = y_l93
            extra["epsg_source"] = 2154

        lieu_dit = str(row.get("lieu-dit") or "").strip()
        if lieu_dit:
            extra["lieu_dit"] = lieu_dit

        raw_parts = [f"{col}={row.get(col)}" for col in list(columns)[:10] if row.get(col) is not None and not (isinstance(row.get(col), float) and pd.isna(row.get(col)))]

        return RawRecord(
            raw_text=" | ".join(raw_parts),
            commune=commune or None,
            type_mention=type_mention or "nécropole",
            periode_mention=periode or None,
            latitude_raw=None,
            longitude_raw=None,
            source_path=path_str,
            extraction_method="ods",
            extra=extra,
        )

    def _get_mapped(self, row, target: str) -> str | None:
        for src_col, tgt in self._column_mapping.items():
            if tgt == target:
                val = row.get(src_col)
                if val is not None and not (isinstance(val, float) and pd.isna(val)):
                    return str(val).strip()
        return None

    @staticmethod
    def _to_float(val: str | None) -> float | None:
        if not val:
            return None
        try:
            return float(str(val).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return None
