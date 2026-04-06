"""Extract site records from Gallica metadata (communes in titles, geographic scope)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)

_COMMUNE_PAT = re.compile(
    r"[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ][\wÀ-ÿ'\-]+(?:\s*[-–]\s*[\wÀ-ÿ'\-]+)?",
)

_STOPWORDS = frozenset({
    "Carte", "Gaule", "Nouvelle", "Musée", "Alsace", "France", "Europe",
    "Manuel", "Archéologie", "Bronzes", "Essai", "Cahiers", "Histoire",
    "Ancienne", "Premier", "Haut", "Bas", "Étude", "Éditions",
    "Série", "Table", "Les", "Des", "Sur", "Par", "Dans", "Pour",
})


class GallicaMetadataExtractor:
    """Generate RawRecords from structured Gallica metadata (communes in geographic_scope)."""

    def extract(self, metadata_path: Path) -> list[RawRecord]:
        if not metadata_path.is_file():
            logger.warning("Gallica metadata file not found: %s", metadata_path)
            return []

        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        docs = data.get("documents", [])
        records: list[RawRecord] = []

        for doc in docs:
            ark = doc.get("ark", "")
            title = doc.get("title", "")
            scope = doc.get("geographic_scope", "")
            communes_field = doc.get("communes_mentioned", [])
            mentions = doc.get("mentions_found", [])
            relevance = doc.get("relevance", "")
            categories = doc.get("categories", [])

            communes = list(communes_field)
            if scope and not communes:
                communes = self._parse_communes(scope)

            for commune in communes:
                type_mention = self._infer_type(mentions, categories, commune)
                records.append(
                    RawRecord(
                        raw_text=f"{title} — {scope}",
                        commune=commune,
                        type_mention=type_mention,
                        source_path=f"gallica_metadata:{ark}",
                        extraction_method="gallica_metadata",
                        ark_id=ark,
                        context_text=title,
                        extra={
                            "authors": doc.get("authors", []),
                            "year": doc.get("year"),
                            "relevance": relevance,
                        },
                    )
                )

        logger.info("GallicaMetadataExtractor produced %d records from %d documents", len(records), len(docs))
        return records

    def _parse_communes(self, scope: str) -> list[str]:
        parts = re.split(r"[,;/()]", scope)
        communes: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = _COMMUNE_PAT.match(part)
            if m:
                name = m.group()
                if name not in _STOPWORDS and len(name) > 2 and not re.match(r"^\d", name):
                    communes.append(name)
        return communes

    def _infer_type(self, mentions: list[str], categories: list[str], commune: str) -> str | None:
        for m in mentions:
            if commune.lower() in m.lower():
                for kw in ("nécropole", "oppidum", "habitat", "tumulus", "sanctuaire", "dépôt", "atelier"):
                    if kw in m.lower():
                        return kw
        if "bronze" in " ".join(categories).lower():
            return "dépôt"
        return None
