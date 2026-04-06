"""Facade: SRU discovery, IIIF+Tesseract OCR (or texteBrut fallback), mention extraction → ``RawRecord``."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.domain.models.raw_record import RawRecord
from src.infrastructure.extractors.gallica_cache import GallicaCache, normalize_ark_id
from src.infrastructure.extractors.gallica_iiif import GallicaIIIFClient
from src.infrastructure.extractors.gallica_mention_extractor import GallicaSiteMentionExtractor
from src.infrastructure.extractors.gallica_ocr import GallicaOCRClient, OCRQualityScorer
from src.infrastructure.extractors.gallica_sru import GallicaSRUClient
from src.infrastructure.extractors.tesseract_ocr import TesseractOCRClient

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0
_MAX_PAGES = 50
_USER_AGENT = "BaseFerRhin/1.0 (archaeological-research; +https://github.com/BaseFerRhin)"
_PAGE_DELAY = 2.0


class GallicaExtractor:
    """SRU search → per-page OCR (IIIF+Tesseract primary, texteBrut fallback) → mention parsing."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        cache: GallicaCache | None = None,
        max_pages_per_document: int = _MAX_PAGES,
        use_tesseract: bool = True,
    ) -> None:
        self._external_client = client is not None
        self._client = client
        self._cache = cache or GallicaCache()
        self._max_pages = max_pages_per_document
        self._use_tesseract = use_tesseract

    async def extract(self, sru_query: str, ocr_threshold: float = 0.4) -> list[RawRecord]:
        own_client = not self._external_client
        client = self._client or httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            verify=False,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        )
        try:
            return await self._run_pipeline(client, sru_query, ocr_threshold)
        finally:
            if own_client:
                await client.aclose()

    async def _run_pipeline(
        self, client: httpx.AsyncClient, sru_query: str, ocr_threshold: float
    ) -> list[RawRecord]:
        sru = GallicaSRUClient(client)
        ocr_brut = GallicaOCRClient(client, self._cache)
        iiif = GallicaIIIFClient(client, self._cache)
        tesseract = TesseractOCRClient(iiif, self._cache) if self._use_tesseract else None
        scorer = OCRQualityScorer()
        mentions_ex = GallicaSiteMentionExtractor()
        hits: list[RawRecord] = []
        consecutive_captcha = 0

        for meta in await sru.search(sru_query):
            ark = meta.get("ark", "")
            if not ark:
                continue
            norm_ark = normalize_ark_id(ark)
            ark_leaf = norm_ark.split("/")[-1] if "/" in norm_ark else norm_ark
            if not ark_leaf.startswith("bpt6k"):
                logger.info("Skipping non-document ARK %s (notice only)", norm_ark)
                continue

            extra_doc: dict[str, Any] = {
                k: meta[k] for k in ("title", "authors", "dates") if meta.get(k)
            }
            title = meta.get("title", norm_ark)
            logger.info("Processing document: %s (%s)", title, norm_ark)
            consecutive_captcha = 0

            for page in range(1, self._max_pages + 1):
                await asyncio.sleep(_PAGE_DELAY)
                text = await self._get_page_text(
                    tesseract, ocr_brut, norm_ark, page, consecutive_captcha
                )

                if text is None:
                    break
                if text == "":
                    consecutive_captcha += 1
                    if consecutive_captcha >= 3:
                        logger.warning(
                            "3 consecutive empty/captcha pages on %s, switching to next doc", norm_ark
                        )
                        break
                    continue
                consecutive_captcha = 0

                if scorer.score(text) < ocr_threshold:
                    continue
                for row in mentions_ex.extract(text, page):
                    method = "tesseract_iiif" if tesseract else "gallica_ocr"
                    hits.append(
                        RawRecord(
                            raw_text=row["context_text"],
                            commune=row["commune"],
                            type_mention=row["type_mention"],
                            source_path=f"gallica:{norm_ark}",
                            page_number=row["page_number"],
                            extraction_method=method,
                            ark_id=norm_ark,
                            context_text=row["context_text"],
                            extra=extra_doc,
                        )
                    )
        logger.info("GallicaExtractor produced %d raw records", len(hits))
        return hits

    async def _get_page_text(
        self,
        tesseract: TesseractOCRClient | None,
        ocr_brut: GallicaOCRClient,
        ark: str,
        page: int,
        consecutive_captcha: int,
    ) -> str | None:
        """Return page text, empty string for CAPTCHA/empty, None if page doesn't exist."""
        if tesseract:
            return await self._try_tesseract(tesseract, ark, page)
        return await self._try_texte_brut(ocr_brut, ark, page)

    async def _try_tesseract(
        self, tesseract: TesseractOCRClient, ark: str, page: int
    ) -> str | None:
        try:
            text = await tesseract.ocr_page(ark, page)
            return text
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code == 404:
                return None
            if code in (403, 429):
                logger.warning("IIIF %d on %s p%d, waiting 15s", code, ark, page)
                await asyncio.sleep(15)
                try:
                    return await tesseract.ocr_page(ark, page)
                except httpx.HTTPStatusError:
                    logger.warning("Still blocked on %s p%d, skipping doc", ark, page)
                    return None
            raise

    async def _try_texte_brut(
        self, ocr: GallicaOCRClient, ark: str, page: int
    ) -> str | None:
        try:
            text = await ocr.fetch_ocr_text(ark, page)
            return text
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code == 404:
                return None
            if code in (429, 403):
                logger.warning("texteBrut %d on %s p%d", code, ark, page)
                await asyncio.sleep(10)
                try:
                    return await ocr.fetch_ocr_text(ark, page)
                except httpx.HTTPStatusError:
                    return None
            raise
