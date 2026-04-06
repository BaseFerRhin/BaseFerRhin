"""SRU search client for Gallica."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from lxml import etree

from src.infrastructure.extractors.gallica_cache import gallica_http_semaphore, normalize_ark_id

logger = logging.getLogger(__name__)

SRU_BASE = "https://gallica.bnf.fr/SRU"
_PAGE_SIZE = 50


class GallicaSRUClient:
    """Query Gallica SRU and parse bibliographic records."""

    def __init__(self, client: httpx.AsyncClient, base_url: str = SRU_BASE) -> None:
        self._client = client
        self._base_url = base_url

    def _parse_record(self, rec: Any) -> dict[str, str] | None:
        titles: list[str] = []
        authors: list[str] = []
        dates: list[str] = []
        ark: str | None = None
        for el in rec.iter():
            if not isinstance(el.tag, str):
                continue
            local = etree.QName(el).localname
            text = (el.text or "").strip()
            if not text:
                continue
            if local == "identifier" and "ark:/" in text:
                ark = normalize_ark_id(text)
            elif local == "title":
                titles.append(text)
            elif local == "creator":
                authors.append(text)
            elif local == "date":
                dates.append(text)
        if not ark:
            return None
        return {
            "ark": ark,
            "title": "; ".join(titles),
            "authors": "; ".join(authors),
            "dates": "; ".join(dates),
        }

    @staticmethod
    def _record_elements(root: etree._Element) -> list[Any]:
        for xp in (
            "//*[local-name()='searchRetrieveResponse']/*[local-name()='records']/*[local-name()='record']",
            "//*[local-name()='records']/*[local-name()='record']",
            "//*[local-name()='record']",
        ):
            found = root.xpath(xp)
            if found:
                return found
        return []

    def _parse_xml(self, xml_text: str) -> list[dict[str, str]]:
        root = etree.fromstring(xml_text.encode("utf-8"))
        out: list[dict[str, str]] = []
        for rec in self._record_elements(root):
            parsed = self._parse_record(rec)
            if parsed:
                out.append(parsed)
        return out

    async def search(self, query: str) -> list[dict[str, str]]:
        start_record = 1
        all_rows: list[dict[str, str]] = []
        while True:
            params = urlencode(
                {
                    "operation": "searchRetrieve",
                    "version": "1.2",
                    "query": query,
                    "startRecord": start_record,
                    "maximumRecords": _PAGE_SIZE,
                }
            )
            url = f"{self._base_url}?{params}"
            async with gallica_http_semaphore:
                logger.debug("SRU request startRecord=%s", start_record)
                response = await self._client.get(url)
            response.raise_for_status()
            batch = self._parse_xml(response.text)
            if not batch:
                break
            all_rows.extend(batch)
            if len(batch) < _PAGE_SIZE:
                break
            start_record += _PAGE_SIZE
        logger.info("SRU search returned %d records", len(all_rows))
        return all_rows
