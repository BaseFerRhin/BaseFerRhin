"""Resolve ``SourceExtractor`` by file extension."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import SourceExtractor
from .csv_extractor import CSVExtractor
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class UnsupportedFormatError(ValueError):
    """Raised when no extractor is registered for the file extension."""


class ExtractorFactory:
    """Returns the appropriate extractor for a given path."""

    def __init__(self, csv_column_mapping: dict[str, str] | None = None) -> None:
        self._csv_mapping = csv_column_mapping

    def get_extractor(self, path: Path) -> SourceExtractor:
        ext = path.suffix.lower()
        if ext == ".pdf":
            return PDFExtractor()
        if ext in (".csv", ".xlsx"):
            return CSVExtractor(column_mapping=self._csv_mapping)
        logger.warning("unsupported format: %s", ext)
        raise UnsupportedFormatError(f"No extractor for extension {ext!r}: {path}")
