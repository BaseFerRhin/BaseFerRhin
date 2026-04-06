"""IIIF full-size JPEG download with disk cache."""

from __future__ import annotations

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.infrastructure.extractors.gallica_cache import GallicaCache, normalize_ark_id

logger = logging.getLogger(__name__)


class GallicaIIIFClient:
    """Retrieve ``.../full/max/0/default.jpg`` tiles into the Gallica cache."""

    def __init__(self, client: httpx.AsyncClient, cache: GallicaCache | None = None) -> None:
        self._client = client
        self._cache = cache or GallicaCache()

    def _url(self, norm_ark: str, page: int) -> str:
        return (
            f"https://gallica.bnf.fr/iiif/ark:/{norm_ark}/f{page}/full/max/0/default.jpg"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def download_page_image(self, ark_id: str, page: int) -> bytes:
        norm = normalize_ark_id(ark_id)
        url = self._url(norm, page)
        data = await self._cache.get_or_fetch(self._client, url, ark_id, f"f{page}.jpg")
        logger.info("IIIF page %s f%s (%d bytes)", ark_id, page, len(data))
        return data
