"""Heuristic extraction of commune + site-type phrases from Gallica OCR."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SITE_TYPES = (
    r"habitat|oppidum|nécropole|necropole|tumulus|enceinte|établissement|etablissement|"
    r"sépulture|sepulture|nécropoles|necropoles|site\s+archéologique|site\s+archeologique|"
    r"tumuli|oppida|habitats|sanctuaire|atelier|dépôt|depot|fortification|fossé|fosse|"
    r"camp|castellum|villa|vicus|ferme|grange|four|fourneau|mine|carrière|rempart|murus"
)

_COMMUNE = (
    r"(?P<commune>[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ][\wÀ-ÿ'\-]+"
    r"(?:\s*[-–]\s*[\wÀ-ÿ'\-]+)?"
    r"(?:\s+(?:de|d'|du|la|le|les|sur|sous|am|bei|im)\s+[\wÀ-ÿ'\-]+){0,2}"
    r"(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ][\wÀ-ÿ'\-]+){0,2})"
)

_COMMUNE_REV = (
    r"(?P<commune>[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ][\wÀ-ÿ'\-]+"
    r"(?:\s*[-–]\s*[\wÀ-ÿ'\-]+)?"
    r"(?:\s+(?:de|d'|du|la|le|les|sur|sous|am|bei|im)\s+[\wÀ-ÿ'\-]+){0,2}"
    r"(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ][\wÀ-ÿ'\-]+){0,2})"
)

# commune → type (original direction)
_PAT_FWD = re.compile(
    rf"{_COMMUNE}.{{0,160}}?\b(?P<type>{_SITE_TYPES})\b",
    re.IGNORECASE | re.DOTALL,
)

# type → commune  (reverse: "nécropole de Strasbourg-Koenigshoffen")
_PAT_REV = re.compile(
    rf"\b(?P<type>{_SITE_TYPES})\b"
    rf"(?:\s+(?:de|du|d'|des|à|a|près\s+de|near|bei|von|in)\s+)?"
    rf".{{0,80}}?"
    rf"{_COMMUNE_REV}",
    re.IGNORECASE | re.DOTALL,
)

# "à/de COMMUNE" followed by archaeological context keyword
_PAT_PREP = re.compile(
    r"(?:(?:fouill[eé]s?|découvert[es]?|trouvé[es]?|mis\s+au\s+jour|exhumé[es]?)"
    r".{0,60}?"
    r"(?:à|de|près\s+de)\s+)"
    + _COMMUNE_REV,
    re.IGNORECASE | re.DOTALL,
)


class GallicaSiteMentionExtractor:
    """Regex-based mentions: multiple patterns for commune + archaeological keyword."""

    def extract(self, ocr_text: str, page_number: int) -> list[dict[str, Any]]:
        mentions: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for pat in (_PAT_FWD, _PAT_REV):
            for m in pat.finditer(ocr_text):
                commune = (m.group("commune") or "").strip()
                typ = (m.group("type") or "").strip()
                key = (commune.lower(), typ.lower())
                if key in seen:
                    continue
                seen.add(key)
                start, end = max(0, m.start() - 80), min(len(ocr_text), m.end() + 80)
                ctx = ocr_text[start:end].replace("\n", " ")
                mentions.append(
                    {
                        "commune": commune,
                        "type_mention": typ,
                        "context_text": ctx.strip(),
                        "page_number": page_number,
                    }
                )

        for m in _PAT_PREP.finditer(ocr_text):
            commune = (m.group("commune") or "").strip()
            key = (commune.lower(), "fouille")
            if key in seen:
                continue
            seen.add(key)
            start, end = max(0, m.start() - 40), min(len(ocr_text), m.end() + 80)
            ctx = ocr_text[start:end].replace("\n", " ")
            mentions.append(
                {
                    "commune": commune,
                    "type_mention": "site archéologique",
                    "context_text": ctx.strip(),
                    "page_number": page_number,
                }
            )

        logger.debug("Found %d mentions on page %s", len(mentions), page_number)
        return mentions
