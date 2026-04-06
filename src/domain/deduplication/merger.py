"""Merge two Site records into one consolidated record."""

from __future__ import annotations

import json
import logging

from src.domain.models import PhaseOccupation, Site, Source

logger = logging.getLogger(__name__)


def _filled_field_count(site: Site) -> int:
    data = site.model_dump(mode="python")
    skip = {"phases", "sources"}
    n = 0
    for k, v in data.items():
        if k in skip:
            continue
        if v is None:
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        n += 1
    return n


def _phase_key(p: PhaseOccupation) -> str:
    d = p.model_dump(mode="json")
    for k in ("site_id", "phase_id", "date_creation", "date_maj"):
        d.pop(k, None)
    return json.dumps(d, sort_keys=True)


class SiteMerger:
    def merge(self, primary: Site, secondary: Site) -> Site:
        if _filled_field_count(secondary) > _filled_field_count(primary):
            primary, secondary = secondary, primary
            logger.debug("swap primary/secondary: primary=%s", primary.site_id)

        pdata = primary.model_dump(mode="python")
        sdata = secondary.model_dump(mode="python")

        for key in (
            "description",
            "surface_m2",
            "altitude_m",
            "statut_fouille",
            "commentaire_qualite",
        ):
            if pdata.get(key) is None and sdata.get(key) is not None:
                pdata[key] = sdata[key]

        if not pdata.get("region_admin") and sdata.get("region_admin"):
            pdata["region_admin"] = sdata["region_admin"]

        seen_ids: set[str] = {s.source_id for s in primary.sources}
        merged_sources: list[Source] = list(primary.sources)
        for src in secondary.sources:
            if src.source_id not in seen_ids:
                seen_ids.add(src.source_id)
                merged_sources.append(src.model_copy(update={"site_id": primary.site_id}))

        variantes = list(pdata.get("variantes_nom") or [])
        for v in secondary.variantes_nom:
            if v and v not in variantes:
                variantes.append(v)
        if secondary.nom_site and secondary.nom_site != primary.nom_site and secondary.nom_site not in variantes:
            variantes.append(secondary.nom_site)
        pdata["variantes_nom"] = variantes

        phase_keys: set[str] = {_phase_key(p) for p in primary.phases}
        merged_phases = list(primary.phases)
        for ph in secondary.phases:
            k = _phase_key(ph)
            if k not in phase_keys:
                phase_keys.add(k)
                merged_phases.append(ph.model_copy(update={"site_id": primary.site_id}))

        ext = dict(pdata.get("identifiants_externes") or {})
        ext.update(sdata.get("identifiants_externes") or {})
        pdata["identifiants_externes"] = ext
        pdata["sources"] = merged_sources
        pdata["phases"] = merged_phases

        return Site.model_validate(pdata)
