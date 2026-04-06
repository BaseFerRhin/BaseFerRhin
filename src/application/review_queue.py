"""Human review queue for pipeline exceptions and borderline cases."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ReviewQueue:
    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def add(self, site_data: dict, step: str, reason: str) -> None:
        self._entries.append(
            {
                "site_data": site_data,
                "step": step,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._entries, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("wrote %d review entries to %s", len(self._entries), path)

    @classmethod
    def load(cls, path: Path) -> ReviewQueue:
        q = cls()
        if path.is_file():
            q._entries = json.loads(path.read_text(encoding="utf-8"))
        return q
