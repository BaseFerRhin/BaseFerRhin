"""Helpers for ``pipeline`` (keeps ``pipeline.py`` under 200 lines)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from src.application.config import PipelineConfig
from src.application.review_queue import ReviewQueue
from src.domain.models import Site, Source
from src.domain.models.enums import NiveauConfiance, PrecisionLocalisation, TypeSource
from src.domain.models.raw_record import RawRecord
from src.domain.validators import validate_chronology, validate_coordinates
from src.infrastructure.geocoding.ban import BANGeocoder


def pack_state(state: dict[str, Any]) -> dict[str, Any]:
    rr, sites = state.get("raw_records") or [], state.get("sites") or []
    return {
        "raw_records": [asdict(r) if isinstance(r, RawRecord) else r for r in rr],
        "sites": [s.model_dump(mode="json") if isinstance(s, Site) else s for s in sites],
    }


def unpack_state(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_records": [RawRecord(**r) for r in data.get("raw_records") or []],
        "sites": [Site.model_validate(s) for s in data.get("sites") or []],
    }


def checksum(state: dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(pack_state(state), sort_keys=True, default=str).encode()).hexdigest()


def source_for_record(rec: RawRecord, site_id: str) -> Source:
    ts = (
        TypeSource.GALLICA_CAG
        if rec.extraction_method == "gallica_ocr"
        else TypeSource.PUBLICATION
        if rec.extraction_method == "pdf"
        else TypeSource.TABLEUR
    )
    return Source(
        source_id=f"{site_id}-SRC1",
        site_id=site_id,
        reference=rec.source_path or "unknown",
        type_source=ts,
        ark_gallica=rec.ark_id,
        page_gallica=rec.page_number,
        niveau_confiance=NiveauConfiance.MOYEN,
    )


def site_id(rec: RawRecord) -> str:
    k = f"{rec.source_path}|{rec.page_number}|{rec.raw_text[:500]}"
    return "SITE-" + hashlib.md5(k.encode()).hexdigest()[:16]


def apply_extract(state: dict[str, Any], review: ReviewQueue) -> dict[str, Any]:
    kept: list[RawRecord] = []
    for rec in state["raw_records"]:
        if (rec.raw_text or "").strip() or rec.commune:
            kept.append(rec)
        else:
            review.add(asdict(rec), "EXTRACT", "empty raw_text and commune")
    return {**state, "raw_records": kept}


def apply_geocode(state: dict[str, Any], config: PipelineConfig, review: ReviewQueue) -> dict[str, Any]:
    path = config.geocoder_cache_path
    cache: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    geo, out = BANGeocoder(), []
    for site in state["sites"]:
        if site.latitude is not None and site.longitude is not None or not site.commune.strip():
            out.append(site)
            continue
        key = site.commune.strip().lower()
        if key in cache:
            lat, lon = cache[key]["latitude"], cache[key]["longitude"]
        elif hit := geo.geocode(site.commune, site.nom_site, site.pays.value):
            lat, lon = hit.latitude, hit.longitude
            cache[key] = {"latitude": lat, "longitude": lon}
        else:
            review.add(site.model_dump(mode="json"), "GEOCODE", "ban_lookup_failed")
            out.append(site)
            continue
        out.append(
            site.model_copy(
                update={
                    "latitude": lat,
                    "longitude": lon,
                    "precision_localisation": PrecisionLocalisation.CENTROIDE,
                }
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return {**state, "sites": out}


def apply_validate(state: dict[str, Any], review: ReviewQueue) -> dict[str, Any]:
    for site in state["sites"]:
        sd = site.model_dump(mode="json")
        for ph in site.phases:
            for w in validate_chronology(ph):
                review.add(sd, "VALIDATE", f"chrono:{w.field}:{w.message}")
        for w in validate_coordinates(site.latitude, site.longitude, site.region_admin):
            review.add(sd, "VALIDATE", f"geo:{w.field}:{w.message}")
    return state
