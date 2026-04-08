"""Parser for CAG (Carte Archéologique de la Gaule) text into site notices."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)

_COMMUNE_RE = re.compile(r"^(\d{3})\s*[-–—]\s*(.+)$", re.MULTILINE)
_LIEU_DIT_RE = re.compile(
    r"\((\d{3}\s*[A-Z]{2}(?:,\s*\d{3}\s*[A-Z]{2})*)\)\s*[-–—]?\s*"
    r"(?:Au[x]?\s+lieu[x]?-dit[s]?\s+)?(.+?)(?:\.|,\s*(?:en|à|vers|entre|des|dans|un|une|le|la|les|on|il|G\.|Ch\.|J\.|A\.))",
    re.IGNORECASE,
)
_SUB_NOTICE_SPLIT_RE = re.compile(
    r"\n\s*\((\d{3}\s*[A-Z]{2}(?:,\s*\d{3}\s*[A-Z]{2})*)\)\s*[-–—]?\s*"
)
_BIBLIO_RE = re.compile(r"([A-Z][a-zà-ÿ]+(?:\s+et\s+alii)?,\s*\d{4}[a-z]?)")
_DATATION_KEYWORDS = re.compile(
    r"(?i)\b(?:hallstatt|la\s+tène|âge\s+du\s+fer|âge\s+du\s+bronze|"
    r"protohistor|gallo[- ]?romain|néolith|tumulus|Ha\s*[CD]\d?|LT\s*[A-D]\d?|"
    r"premier\s+âge|second\s+âge)\b"
)
_VESTIGES_KEYWORDS = re.compile(
    r"(?i)\b(?:tumulus|tertre|sépulture|nécropole|habitat|oppidum|"
    r"fortification|enceinte|silo|fosse|four|atelier|dépôt|"
    r"tombe|inhumation|incinération|urne|céramique|tessons?|"
    r"fibule|bracelet|épée|monnaie)\b"
)


class CAGNoticeExtractor:
    """Parse CAG text into individual site notices as RawRecords."""

    def __init__(self, *, source_label: str = "cag_68") -> None:
        self._source_label = source_label

    def supported_formats(self) -> list[str]:
        return [".doc", ".txt"]

    def extract_from_text(self, text: str, source_path: str) -> list[RawRecord]:
        """Parse full CAG text into notice-level and sub-notice-level records."""
        notices = self._split_into_notices(text)
        records: list[RawRecord] = []

        for commune_id, commune_name, notice_text in notices:
            sub_notices = self._split_sub_notices(notice_text, commune_name.strip())
            if not sub_notices:
                sub_notices = [(None, notice_text)]

            for lieu_dit, sub_text in sub_notices:
                biblio = _BIBLIO_RE.findall(sub_text)
                datation_matches = _DATATION_KEYWORDS.findall(sub_text)
                vestiges_matches = _VESTIGES_KEYWORDS.findall(sub_text)

                if not datation_matches and not vestiges_matches:
                    continue

                extra: dict = {
                    "cag_commune_id": commune_id,
                    "source_label": self._source_label,
                }
                if lieu_dit:
                    extra["lieu_dit"] = lieu_dit
                if biblio:
                    extra["bibliographie"] = biblio
                if datation_matches:
                    extra["datation_mentions"] = list(set(datation_matches))
                if vestiges_matches:
                    extra["vestiges_mentions"] = list(set(vestiges_matches))

                type_mention = self._guess_type(vestiges_matches)
                periode_mention = " / ".join(sorted(set(datation_matches))) if datation_matches else None

                records.append(RawRecord(
                    raw_text=sub_text[:500],
                    commune=commune_name.strip(),
                    type_mention=type_mention,
                    periode_mention=periode_mention,
                    latitude_raw=None,
                    longitude_raw=None,
                    source_path=source_path,
                    extraction_method=f"cag_notice_{self._source_label}",
                    extra=extra,
                ))

        logger.info("CAG %s: %d commune notices → %d records with vestiges",
                     self._source_label, len(notices), len(records))
        return records

    def _split_into_notices(self, text: str) -> list[tuple[str, str, str]]:
        """Split text by commune header pattern 'NNN — COMMUNE_NAME'."""
        matches = list(_COMMUNE_RE.finditer(text))
        if not matches:
            return []

        notices: list[tuple[str, str, str]] = []
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            notice_text = text[start:end].strip()
            notices.append((m.group(1), m.group(2), notice_text))

        return notices

    @staticmethod
    def _split_sub_notices(notice_text: str, commune: str) -> list[tuple[str | None, str]]:
        """Split a commune notice into sub-notices by lieu-dit codes like (004 AH)."""
        parts = _SUB_NOTICE_SPLIT_RE.split(notice_text)
        if len(parts) <= 1:
            m = _LIEU_DIT_RE.search(notice_text)
            if m:
                return [(m.group(2).strip(), notice_text)]
            return []

        result: list[tuple[str | None, str]] = []
        i = 0
        if parts[0].strip():
            result.append((None, parts[0].strip()))
            i = 1

        while i < len(parts) - 1:
            code = parts[i].strip()
            text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            lieu_dit_m = _LIEU_DIT_RE.search(text)
            lieu_dit = lieu_dit_m.group(2).strip() if lieu_dit_m else code
            result.append((lieu_dit, f"({code}) {text}"))
            i += 2

        return result

    @staticmethod
    def _guess_type(vestiges: list[str]) -> str:
        vestiges_lower = {v.lower() for v in vestiges}
        if vestiges_lower & {"tumulus", "tertre", "nécropole", "tombe", "sépulture", "inhumation", "incinération", "urne"}:
            return "nécropole"
        if vestiges_lower & {"oppidum", "fortification", "enceinte"}:
            return "oppidum"
        if vestiges_lower & {"habitat", "silo", "fosse", "four"}:
            return "habitat"
        if vestiges_lower & {"atelier"}:
            return "atelier"
        if vestiges_lower & {"dépôt"}:
            return "dépôt"
        return "indéterminé"
