"""Composite similarity scoring for site deduplication."""

from __future__ import annotations

import logging
import math
from typing import Final

from rapidfuzz import fuzz

from src.domain.models.site import Site

logger = logging.getLogger(__name__)

_EARTH_RADIUS_KM: Final[float] = 6371.0


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return _EARTH_RADIUS_KM * c


class SimilarityScorer:
    """40/30/30 when both have coords; if both lack coords, geo → name (70/30)."""

    def score(self, site_a: Site, site_b: Site) -> float:
        name_sim = fuzz.token_sort_ratio(site_a.nom_site, site_b.nom_site) / 100.0
        commune_sim = fuzz.token_sort_ratio(site_a.commune, site_b.commune) / 100.0
        a_geo = site_a.latitude is not None and site_a.longitude is not None
        b_geo = site_b.latitude is not None and site_b.longitude is not None
        both_geo = a_geo and b_geo
        both_lack = not a_geo and not b_geo
        if both_geo:
            dist = _haversine(
                float(site_a.latitude),
                float(site_a.longitude),
                float(site_b.latitude),
                float(site_b.longitude),
            )
            geo_sim = 1.0 - min(dist, 50.0) / 50.0
            total = 0.4 * name_sim + 0.3 * commune_sim + 0.3 * geo_sim
        elif both_lack:
            total = 0.7 * name_sim + 0.3 * commune_sim
        else:
            total = (0.4 * name_sim + 0.3 * commune_sim) / 0.7
        logger.debug(
            "score site_a=%s site_b=%s name=%.3f commune=%.3f total=%.3f",
            site_a.site_id,
            site_b.site_id,
            name_sim,
            commune_sim,
            total,
        )
        return total
