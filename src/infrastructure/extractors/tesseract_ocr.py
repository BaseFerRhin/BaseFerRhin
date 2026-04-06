"""Local Tesseract OCR on Gallica IIIF page images."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

import pytesseract
from PIL import Image

from src.infrastructure.extractors.gallica_cache import GallicaCache, normalize_ark_id
from src.infrastructure.extractors.gallica_iiif import GallicaIIIFClient

logger = logging.getLogger(__name__)

_DEFAULT_LANGS = "fra+deu"
_DPI_THRESHOLD = 150


class TesseractOCRClient:
    """Download page via IIIF, run Tesseract locally, cache plain-text result."""

    def __init__(
        self,
        iiif: GallicaIIIFClient,
        cache: GallicaCache | None = None,
        langs: str = _DEFAULT_LANGS,
    ) -> None:
        self._iiif = iiif
        self._cache = cache or GallicaCache()
        self._langs = langs

    async def ocr_page(self, ark_id: str, page: int) -> str:
        cache_file = f"f{page}.tesseract.txt"
        cache_path = self._cache.path_for(ark_id, cache_file)
        if cache_path.exists():
            logger.debug("Tesseract cache hit %s", cache_path)
            return cache_path.read_text(encoding="utf-8")

        jpeg_bytes = await self._iiif.download_page_image(ark_id, page)
        text = self._run_ocr(jpeg_bytes, ark_id, page)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        logger.info("Tesseract OCR %s p%d -> %d chars", ark_id, page, len(text))
        return text

    def _run_ocr(self, image_bytes: bytes, ark_id: str, page: int) -> str:
        img = Image.open(BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w > 4000 or h > 6000:
            ratio = min(4000 / w, 6000 / h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            logger.debug("Resized %s p%d from %dx%d to %dx%d", ark_id, page, w, h, img.width, img.height)

        text = pytesseract.image_to_string(
            img,
            lang=self._langs,
            config="--psm 1 --oem 1",
        )
        return text.strip()
