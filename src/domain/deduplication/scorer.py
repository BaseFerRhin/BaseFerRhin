"""Composite similarity scoring for site deduplication (Lambert-93)."""

from __future__ import annotations

import logging
import math

from rapidfuzz import fuzz

from src.domain.models.site import Site

logger = logging.getLogger(__name__)


def _distance_l93_km(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance in kilometers between two Lambert-93 points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 1000.0


class SimilarityScorer:
    """40/30/30 when both have coords; if both lack coords, geo → name (70/30)."""

    def score(self, site_a: Site, site_b: Site) -> float:
        name_sim = fuzz.token_sort_ratio(site_a.nom_site, site_b.nom_site) / 100.0
        commune_sim = fuzz.token_sort_ratio(site_a.commune, site_b.commune) / 100.0
        a_geo = site_a.x_l93 is not None and site_a.y_l93 is not None
        b_geo = site_b.x_l93 is not None and site_b.y_l93 is not None
        both_geo = a_geo and b_geo
        both_lack = not a_geo and not b_geo
        if both_geo:
            dist = _distance_l93_km(
                float(site_a.x_l93),
                float(site_a.y_l93),
                float(site_b.x_l93),
                float(site_b.y_l93),
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
