"""Plain-text OCR download and simple French dictionary quality score."""

from __future__ import annotations

import logging
import re

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.infrastructure.extractors.gallica_cache import (
    GallicaCache,
    gallica_http_semaphore,
    normalize_ark_id,
)

logger = logging.getLogger(__name__)

_WORD = re.compile(
    r"\b[\wàâäéèêëïîôùûüçœæÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ'-]+\b",
    re.IGNORECASE,
)

# ~200 frequent French tokens (lowercase) for OCR confidence proxy
_F = (
    "le la les un une des du de d l à au aux en et ou mais donc car si alors comme "
    "que qui quoi dont où ce cette ces cet son sa ses leur leurs mon ma mes ton ta tes "
    "notre nos votre vos il elle ils elles on nous vous je tu lui eux y en ne pas plus "
    "moins très aussi bien déjà encore toujours jamais rien tout toute tous autres autre "
    "même même grand grande petit petite nouveau nouvelle ancien ancienne premier première "
    "deux trois quatre cinq six sept huit neuf dix année années jour jours temps vie monde "
    "pays ville commune région nord sud est ouest rhin alsace france français française "
    "allemand allemande europe européen histoire archéologie site fouille découverte objet "
    "tombe sépulture nécropole habitat oppidum tumulus enceinte mur fossé tranchée couche "
    "couches niveau terre pierre bronze fer céramique poterie métal os bois pierres âge "
    "antique médiéval moderne ancien temple église chapelle château maison village hameau "
    "campagne forêt rivière fleuve colline montagne plaine vallée route chemin lieu endroit "
    "parti partie période phase type forme ensemble plusieurs certains certaine quelques "
    "chaque aucun aucune selon pendant avant après depuis jusqu vers entre sous sur dans "
    "par pour sans avec contre chez près loin dedans dehors aujourd hier demain ici là "
    "ainsi ainsi donc lors lorsque lorsqu lorsqu alors cependant toutefois néanmoins "
    "cependant or ni soit soit étant été être suis es est sommes êtes sont étais étions "
    "serai seras sera serons serez seront avais avait avions avaient ai a as avons ont "
    "fais fait faisons font dis dit disent va vont viens vient venons viennent peux peut "
    "pouvons peuvent dois doit devons doivent veux veut voulons veulent sais sait savons "
    "savent vois voit voyons voient crois croit croyons croient pense pensent trouve "
    "trouvent semble semblent reste restent paraît paraissent devient deviennent tient "
    "tiennent mettent met prend prennent donne donnent laisse laissent passe passent "
    "arrive arrivent entre entrent sort sortent monte montent descend descendent "
    "commence commencent continue continuent finissent finit termine terminent "
    "chose choses cas fait faits point question problème solution résultat exemple "
    "nombre nombreux nombreuse étude travaux travail recherche publication rapport "
    "carte plan figure photo image dessin carte mention mentionné indique indiqué "
    "localisation situation position coordonnées latitude longitude nordique celtique "
    "gallo romain romaine gallo romaine protohistoire protohistorique préhistoire "
    "néolithique hallstatt latène second premier siècle siècles millénaire millénaires "
)
FRENCH_COMMON_WORDS: frozenset[str] = frozenset(_F.split())


class OCRQualityScorer:
    """Ratio of token hits against a small French lexicon (0.0–1.0)."""

    def __init__(self, dictionary: frozenset[str] | None = None) -> None:
        self._dictionary = dictionary or FRENCH_COMMON_WORDS

    def score(self, text: str) -> float:
        tokens = [t.lower() for t in _WORD.findall(text)]
        if not tokens:
            return 0.0
        hits = sum(1 for t in tokens if t in self._dictionary)
        return hits / len(tokens)


class GallicaOCRClient:
    """Fetch ``texteBrut`` pages with retries and optional disk cache."""

    def __init__(self, client: httpx.AsyncClient, cache: GallicaCache | None = None) -> None:
        self._client = client
        self._cache = cache or GallicaCache()

    def _url(self, norm_ark: str, page: int) -> str:
        return f"https://gallica.bnf.fr/ark:/{norm_ark}/f{page}.texteBrut"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _download(self, url: str) -> bytes:
        async with gallica_http_semaphore:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.content

    async def fetch_ocr_text(self, ark_id: str, page: int) -> str:
        norm = normalize_ark_id(ark_id)
        filename = f"f{page}.texteBrut"
        path = self._cache.path_for(ark_id, filename)
        if path.exists():
            logger.info("OCR cache hit %s", path)
            return path.read_text(encoding="utf-8", errors="replace")
        url = self._url(norm, page)
        data = await self._download(url)
        text = data.decode("utf-8", errors="replace")
        if "Vérification de sécurité" in text or "<html" in text[:200].lower():
            logger.warning("CAPTCHA page detected for %s p%d, skipping", ark_id, page)
            return ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("OCR saved %s", path)
        return text
