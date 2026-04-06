"""Aggregate export statistics and Rich console display."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from rich.console import Console
from rich.table import Table

from src.domain.models import Site

logger = logging.getLogger(__name__)


class ExportStats:
    def compute(self, sites: list[Site]) -> dict[str, Any]:
        by_pays: Counter[str] = Counter()
        by_periode: Counter[str] = Counter()
        by_type: Counter[str] = Counter()
        with_coords = 0
        without_coords = 0
        for s in sites:
            by_pays[s.pays.value] += 1
            by_type[s.type_site.value] += 1
            if s.x_l93 is not None and s.y_l93 is not None:
                with_coords += 1
            else:
                without_coords += 1
            for ph in s.phases:
                by_periode[ph.periode.value] += 1
        stats: dict[str, Any] = {
            "total_sites": len(sites),
            "by_pays": dict(by_pays),
            "by_periode": dict(by_periode),
            "by_type_site": dict(by_type),
            "with_coordinates": with_coords,
            "without_coordinates": without_coords,
        }
        logger.debug("export stats computed: %s", stats)
        return stats

    def display(self, stats: dict[str, Any]) -> None:
        console = Console()
        t = Table(title="Export statistics")
        t.add_column("Metric", style="cyan")
        t.add_column("Value", style="white")
        t.add_row("total_sites", str(stats.get("total_sites", 0)))
        t.add_row("with_coordinates", str(stats.get("with_coordinates", 0)))
        t.add_row("without_coordinates", str(stats.get("without_coordinates", 0)))
        console.print(t)
        for title, key in (
            ("By pays", "by_pays"),
            ("By période (phase rows)", "by_periode"),
            ("By type_site", "by_type_site"),
        ):
            sub = Table(title=title)
            sub.add_column("Key")
            sub.add_column("Count", justify="right")
            for k, v in sorted((stats.get(key) or {}).items(), key=lambda x: (-x[1], x[0])):
                sub.add_row(str(k), str(v))
            console.print(sub)
