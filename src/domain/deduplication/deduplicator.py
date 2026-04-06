"""Cluster-based site deduplication with review queue."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.deduplication.merger import SiteMerger, _filled_field_count
from src.domain.deduplication.scorer import SimilarityScorer
from src.domain.models import Site

logger = logging.getLogger(__name__)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._p = list(range(n))

    def find(self, i: int) -> int:
        if self._p[i] != i:
            self._p[i] = self.find(self._p[i])
        return self._p[i]

    def union(self, i: int, j: int) -> None:
        ri, rj = self.find(i), self.find(j)
        if ri != rj:
            self._p[rj] = ri


class SiteDeduplicator:
    def __init__(
        self,
        merge_threshold: float = 0.85,
        review_threshold: float = 0.70,
        scorer: SimilarityScorer | None = None,
        merger: SiteMerger | None = None,
    ) -> None:
        self.merge_threshold = merge_threshold
        self.review_threshold = review_threshold
        self._scorer = scorer or SimilarityScorer()
        self._merger = merger or SiteMerger()
        self.last_report: dict[str, Any] = {}

    def deduplicate(self, sites: list[Site]) -> tuple[list[Site], list[dict[str, Any]]]:
        n = len(sites)
        uf = _UnionFind(n)
        review_pairs: list[dict[str, Any]] = []
        pair_scores: list[tuple[int, int, float]] = []

        for i in range(n):
            for j in range(i + 1, n):
                s = self._scorer.score(sites[i], sites[j])
                pair_scores.append((i, j, s))
                if s >= self.merge_threshold:
                    uf.union(i, j)
                elif s >= self.review_threshold:
                    review_pairs.append(
                        {
                            "site_id_a": sites[i].site_id,
                            "site_id_b": sites[j].site_id,
                            "score": round(s, 4),
                            "nom_site_a": sites[i].nom_site,
                            "nom_site_b": sites[j].nom_site,
                            "commune_a": sites[i].commune,
                            "commune_b": sites[j].commune,
                        }
                    )

        groups: dict[int, list[Site]] = {}
        for i in range(n):
            r = uf.find(i)
            groups.setdefault(r, []).append(sites[i])

        merged: list[Site] = []
        merge_ops = 0
        for grp in groups.values():
            if len(grp) == 1:
                merged.append(grp[0])
            else:
                grp_sorted = sorted(grp, key=_filled_field_count, reverse=True)
                acc = grp_sorted[0]
                for sec in grp_sorted[1:]:
                    acc = self._merger.merge(acc, sec)
                    merge_ops += 1
                merged.append(acc)

        merged_count = sum(1 for g in groups.values() if len(g) > 1)
        report: dict[str, Any] = {
            "input_count": n,
            "output_count": len(merged),
            "clusters_merged": merged_count,
            "pairwise_merges": merge_ops,
            "review_pair_count": len(review_pairs),
            "pairs_compared": len(pair_scores),
            "max_score": max((t[2] for t in pair_scores), default=None),
            "merge_threshold": self.merge_threshold,
            "review_threshold": self.review_threshold,
        }
        self.last_report = report
        logger.info("deduplicate report=%s", report)
        return merged, review_pairs
