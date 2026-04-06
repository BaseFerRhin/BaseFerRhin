"""PDF text and table extraction via pdfplumber."""

from __future__ import annotations

import logging
from pathlib import Path

import pdfplumber

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts page-level text and detected tables from PDF sources."""

    def supported_formats(self) -> list[str]:
        return [".pdf"]

    def extract(self, source_path: Path) -> list[RawRecord]:
        path_str = str(source_path.resolve())
        records: list[RawRecord] = []
        with pdfplumber.open(source_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                tables = page.extract_tables() or []
                extra: dict = {}
                if not text:
                    extra["needs_ocr"] = True
                if tables:
                    extra["tables"] = tables
                records.append(
                    RawRecord(
                        raw_text=text,
                        source_path=path_str,
                        page_number=i,
                        extraction_method="pdf",
                        extra=extra,
                    )
                )
        logger.info("pdf extract: %s pages=%d", source_path.name, len(records))
        return records
