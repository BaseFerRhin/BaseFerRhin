"""Local file cache and HTTP concurrency limit for Gallica downloads."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

gallica_http_semaphore: asyncio.Semaphore = asyncio.Semaphore(2)


def normalize_ark_id(ark: str) -> str:
    """Return ARK segment like ``12148/bpt6k123`` without URL prefix or ``ark:/``."""
    s = ark.strip()
    if "ark:/" in s:
        s = s[s.index("ark:/") + 5:]
    return s.strip("/")


class GallicaCache:
    """Stores raw Gallica payloads under ``data/raw/gallica/{ark_id}/``."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path("data/raw/gallica")

    def path_for(self, ark_id: str, filename: str) -> Path:
        norm = normalize_ark_id(ark_id)
        return self.base_dir.joinpath(*norm.split("/"), filename)

    async def get_or_fetch(self, client: httpx.AsyncClient, url: str, ark_id: str, filename: str) -> bytes:
        path = self.path_for(ark_id, filename)
        if path.exists():
            logger.info("Gallica cache hit: %s", path)
            return path.read_bytes()
        async with gallica_http_semaphore:
            if path.exists():
                return path.read_bytes()
            logger.info("Gallica download: %s -> %s", url, path)
            response = await client.get(url)
            response.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        return path.read_bytes()
