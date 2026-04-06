"""Download and parse Gallica ALTO layout XML."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from lxml import etree
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.infrastructure.extractors.gallica_cache import GallicaCache, normalize_ark_id

logger = logging.getLogger(__name__)


class GallicaALTOClient:
    """Fetch ALTO for a page and return text blocks with bounding boxes."""

    def __init__(self, client: httpx.AsyncClient, cache: GallicaCache | None = None) -> None:
        self._client = client
        self._cache = cache or GallicaCache()

    def _url(self, norm_ark: str, page: int) -> str:
        q = urlencode({"O": norm_ark, "E": "ALTO", "Deb": str(page)})
        return f"https://gallica.bnf.fr/RequestDigitalElement?{q}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_alto_bytes(self, ark_id: str, page: int) -> bytes:
        norm = normalize_ark_id(ark_id)
        url = self._url(norm, page)
        return await self._cache.get_or_fetch(self._client, url, ark_id, f"alto_p{page}.xml")

    @staticmethod
    def _fnum(el: Any, *names: str) -> float:
        for n in names:
            v = el.get(n)
            if v is not None:
                return float(v)
        return 0.0

    def parse_blocks(self, xml_bytes: bytes) -> list[dict[str, Any]]:
        root = etree.fromstring(xml_bytes)
        blocks: list[dict[str, Any]] = []
        for tb in root.xpath("//*[local-name()='TextBlock']"):
            x = self._fnum(tb, "HPOS", "hpos")
            y = self._fnum(tb, "VPOS", "vpos")
            w = self._fnum(tb, "WIDTH", "width")
            h = self._fnum(tb, "HEIGHT", "height")
            parts: list[str] = []
            for s in tb.xpath(".//*[local-name()='String']"):
                c = s.get("CONTENT") or s.get("content") or ""
                if c:
                    parts.append(c)
            text = " ".join(parts).strip()
            if text:
                blocks.append({"text": text, "x": x, "y": y, "width": w, "height": h})
        logger.debug("ALTO parsed %d blocks", len(blocks))
        return blocks

    async def fetch_blocks(self, ark_id: str, page: int) -> list[dict[str, Any]]:
        raw = await self.fetch_alto_bytes(ark_id, page)
        return self.parse_blocks(raw)
