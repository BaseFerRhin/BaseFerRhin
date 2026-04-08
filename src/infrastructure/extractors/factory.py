"""Resolve ``SourceExtractor`` by file extension or explicit type."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domain.models.raw_record import RawRecord

from .base import SourceExtractor
from .csv_extractor import CSVExtractor
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class UnsupportedFormatError(ValueError):
    """Raised when no extractor is registered for the file extension."""


class ExtractorFactory:
    """Returns the appropriate extractor for a given path or source config."""

    def __init__(self, csv_column_mapping: dict[str, str] | None = None) -> None:
        self._csv_mapping = csv_column_mapping

    def get_extractor(self, path: Path, *, source_type: str | None = None, **kwargs: Any) -> SourceExtractor:
        ext_type = source_type or path.suffix.lower().lstrip(".")

        if ext_type == "pdf":
            return PDFExtractor()
        if ext_type in ("csv", "xlsx") and not source_type:
            return CSVExtractor(column_mapping=self._csv_mapping)

        if ext_type == "arkeogis":
            from .arkeogis_extractor import ArkeoGISExtractor
            return ArkeoGISExtractor(**kwargs)
        if ext_type == "patriarche":
            from .patriarche_extractor import PatriarcheExtractor
            return PatriarcheExtractor(**kwargs)
        if ext_type == "dbf":
            from .dbf_extractor import DBFExtractor
            return DBFExtractor(**kwargs)
        if ext_type == "alsace_basel":
            from .alsace_basel_extractor import AlsaceBaselExtractor
            return AlsaceBaselExtractor()
        if ext_type == "bdd_proto_alsace":
            from .thematic_xlsx_extractor import BdDProtoAlsaceExtractor
            return BdDProtoAlsaceExtractor()
        if ext_type == "necropoles":
            from .thematic_xlsx_extractor import NecropoleExtractor
            return NecropoleExtractor(**kwargs)
        if ext_type == "inhumations_silos":
            from .thematic_xlsx_extractor import InhumationsSilosExtractor
            return InhumationsSilosExtractor(**kwargs)
        if ext_type == "habitats_tombes_riches":
            from .thematic_xlsx_extractor import HabitatsTombesRichesExtractor
            return HabitatsTombesRichesExtractor(**kwargs)
        if ext_type == "afeaf":
            from .afeaf_extractor import AFEAFExtractor
            return AFEAFExtractor(**kwargs)
        if ext_type == "ods":
            from .ods_extractor import ODSExtractor
            return ODSExtractor(**kwargs)
        if ext_type == "doc":
            from .doc_extractor import DocExtractor
            return DocExtractor()
        if ext_type == "cag_doc":
            return _CAGDocExtractor(**kwargs)

        if path.suffix.lower() in (".csv", ".xlsx"):
            return CSVExtractor(column_mapping=self._csv_mapping)

        logger.warning("unsupported format: %s (type=%s)", path.suffix, source_type)
        raise UnsupportedFormatError(f"No extractor for type {ext_type!r}: {path}")


class _CAGDocExtractor:
    """Chains DocExtractor (text) + CAGNoticeExtractor (parsing) into RawRecords."""

    def __init__(self, *, source_label: str = "cag_68") -> None:
        from .doc_extractor import DocExtractor
        from .cag_notice_extractor import CAGNoticeExtractor

        self._doc = DocExtractor()
        self._parser = CAGNoticeExtractor(source_label=source_label)

    def supported_formats(self) -> list[str]:
        return [".doc"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        text = self._doc.extract_text(source_path)
        return self._parser.extract_from_text(text, str(source_path.resolve()))
