"""Chronological and geographic filters for raw archaeological records."""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from typing import Sequence

from src.domain.models.raw_record import RawRecord

logger = logging.getLogger(__name__)

_IRON_AGE_RE = re.compile(
    r"(?i)\b(?:hallstatt|ha\s*[cd]\d?|la\s+tène|latène|lt\s*[a-d]\d?|"
    r"âge\s+du\s+fer|age\s+du\s+fer|eisenzeit|"
    r"premier\s+âge|second\s+âge|protohistor)\b"
)

_BRONZE_ONLY_RE = re.compile(
    r"(?i)\b(?:âge\s+du\s+bronze|age\s+du\s+bronze|bronzezeit|"
    r"néolith|paléolith|mésol|chalcolith)\b"
)

_IRON_AGE_DATE_MIN = -800
_IRON_AGE_DATE_MAX = -25

_RHIN_SUP_DEPARTMENTS = {67, 68}
_RHIN_SUP_PAYS = {"FR", "DE", "CH"}


def is_age_du_fer(record: RawRecord) -> bool:
    """Return True if the record is plausibly Iron Age.

    Rejects records whose date range ends before -800 (pure Bronze/Neolithic).
    """
    extra = record.extra or {}

    if record.periode_mention and _IRON_AGE_RE.search(record.periode_mention):
        return True

    phases = extra.get("phases_bool")
    if phases and len(phases) > 0:
        return True

    datation_mentions = extra.get("datation_mentions", [])
    if any(_IRON_AGE_RE.search(m) for m in datation_mentions):
        return True

    debut = extra.get("datation_debut")
    fin = extra.get("datation_fin")
    if debut is not None and fin is not None:
        try:
            d, f = int(debut), int(fin)
            if f <= _IRON_AGE_DATE_MIN:
                return False
            if d > _IRON_AGE_DATE_MAX:
                return False
            return True
        except (TypeError, ValueError):
            pass

    if record.periode_mention and _BRONZE_ONLY_RE.search(record.periode_mention):
        if not _IRON_AGE_RE.search(record.periode_mention):
            return False

    method = record.extraction_method or ""
    if method in ("patriarche", "bdd_proto_alsace", "necropoles", "inhumations_silos", "afeaf"):
        return True

    return False


def filter_records(
    records: Sequence[RawRecord],
    *,
    chrono: bool = True,
    departments: set[int] | None = None,
    pays: set[str] | None = None,
) -> list[RawRecord]:
    """Filter records by chronological and geographic criteria.

    Parameters
    ----------
    chrono : apply Iron Age chronological filter
    departments : retain only these French department codes (e.g. {67, 68})
    pays : retain only these country codes (e.g. {"FR", "DE", "CH"})
    """
    exclusion_log: Counter[str] = Counter()
    source_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "retained": 0, "chrono": 0, "geo": 0})
    accepted: list[RawRecord] = []

    for rec in records:
        src = rec.extraction_method or "unknown"
        source_stats[src]["total"] += 1

        if chrono and not is_age_du_fer(rec):
            exclusion_log["chrono_hors_fer"] += 1
            source_stats[src]["chrono"] += 1
            logger.info(
                "Excluded (chrono: hors périmètre chronologique): source_path=%s commune=%s periode=%s",
                rec.source_path, rec.commune, rec.periode_mention,
            )
            continue

        if departments or pays:
            extra = rec.extra or {}
            rec_pays = extra.get("pays", "").upper()
            dept = _extract_department(rec)

            if pays and rec_pays and rec_pays not in pays:
                exclusion_log["geo_hors_pays"] += 1
                source_stats[src]["geo"] += 1
                logger.info(
                    "Excluded (geo: hors pays): source_path=%s commune=%s pays=%s",
                    rec.source_path, rec.commune, rec_pays,
                )
                continue

            if departments and dept is not None and dept not in departments:
                exclusion_log["geo_hors_departement"] += 1
                source_stats[src]["geo"] += 1
                logger.info(
                    "Excluded (geo: hors département): source_path=%s commune=%s dept=%s",
                    rec.source_path, rec.commune, dept,
                )
                continue

        source_stats[src]["retained"] += 1
        accepted.append(rec)

    for src, stats in source_stats.items():
        logger.info(
            "Source %s: %d/%d retained, %d excluded (chrono: %d, geo: %d)",
            src, stats["retained"], stats["total"],
            stats["chrono"] + stats["geo"], stats["chrono"], stats["geo"],
        )

    logger.info(
        "Filter: %d → %d records (excluded %d)",
        len(records), len(accepted), len(records) - len(accepted),
    )
    return accepted


def _extract_department(rec: RawRecord) -> int | None:
    extra = rec.extra or {}
    dept = extra.get("departement") or extra.get("dept_land")
    if dept:
        try:
            return int(str(dept).strip()[:2])
        except (ValueError, TypeError):
            pass

    ea = extra.get("patriarche_ea", "")
    if ea and len(ea) >= 2:
        try:
            return int(ea[:2])
        except (ValueError, TypeError):
            pass

    return None
