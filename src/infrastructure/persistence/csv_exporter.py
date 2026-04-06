"""Denormalized CSV export: one row per site–phase pair."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.domain.models import Site

logger = logging.getLogger(__name__)


class CSVExporter:
    def export(self, sites: list[Site], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        refs_sep = ";"
        fieldnames = [
            "site_id",
            "nom_site",
            "commune",
            "pays",
            "type_site",
            "latitude",
            "longitude",
            "phase_id",
            "periode",
            "sous_periode",
            "datation_debut",
            "datation_fin",
            "sources_count",
            "source_references",
        ]
        rows_written = 0
        with output_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for s in sites:
                refs = refs_sep.join(src.reference for src in s.sources)
                base = {
                    "site_id": s.site_id,
                    "nom_site": s.nom_site,
                    "commune": s.commune,
                    "pays": s.pays.value,
                    "type_site": s.type_site.value,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "sources_count": len(s.sources),
                    "source_references": refs,
                }
                if not s.phases:
                    row = {**base, **{k: "" for k in fieldnames if k not in base}}
                    w.writerow(row)
                    rows_written += 1
                else:
                    for ph in s.phases:
                        row = {
                            **base,
                            "phase_id": ph.phase_id,
                            "periode": ph.periode.value,
                            "sous_periode": ph.sous_periode or "",
                            "datation_debut": ph.datation_debut,
                            "datation_fin": ph.datation_fin,
                        }
                        w.writerow(row)
                        rows_written += 1
        logger.info("wrote %d rows to %s", rows_written, output_path)
