from typing import Optional

from src.domain.models.enums import Pays, PrecisionLocalisation, TypeSite
from src.domain.models.phase import PhaseOccupation
from src.domain.models.raw_record import RawRecord
from src.domain.models.site import Site
from src.domain.models.source import Source
from src.infrastructure.geocoding.base import wgs84_to_l93

from .periode import PeriodeNormalizer
from .toponymie import ToponymeNormalizer
from .type_site import TypeSiteNormalizer


class SiteNormalizer:
    def __init__(
        self,
        type_normalizer: Optional[TypeSiteNormalizer] = None,
        periode_normalizer: Optional[PeriodeNormalizer] = None,
        toponyme_normalizer: Optional[ToponymeNormalizer] = None,
    ):
        self._type = type_normalizer or TypeSiteNormalizer()
        self._periode = periode_normalizer or PeriodeNormalizer()
        self._toponyme = toponyme_normalizer or ToponymeNormalizer()

    def normalize(self, record: RawRecord, site_id: str, source: Source) -> Site:
        type_site = TypeSite.INDETERMINE
        if record.type_mention:
            type_site = self._type.normalize(record.type_mention)

        periode, sous_periode = self._periode.normalize(
            record.periode_mention or record.raw_text
        )

        commune = record.commune or ""
        variantes: list[str] = []
        if commune:
            commune, variantes = self._toponyme.normalize(commune)

        phases = []
        if periode:
            phases.append(
                PhaseOccupation(
                    phase_id=f"{site_id}-PH1",
                    site_id=site_id,
                    periode=periode,
                    sous_periode=sous_periode,
                )
            )

        x_l93: Optional[float] = None
        y_l93: Optional[float] = None
        extra = record.extra or {}

        if extra.get("x_l93") is not None and extra.get("y_l93") is not None:
            x_l93 = float(extra["x_l93"])
            y_l93 = float(extra["y_l93"])
        elif record.latitude_raw is not None and record.longitude_raw is not None:
            x_l93, y_l93 = wgs84_to_l93(record.longitude_raw, record.latitude_raw)
        identifiants = {}
        if extra.get("patriarche_ea"):
            identifiants["patriarche_ea"] = str(extra["patriarche_ea"])
        if extra.get("patriarche_code_national"):
            identifiants["patriarche_code_national"] = str(extra["patriarche_code_national"])
        if extra.get("SITE_AKG_ID"):
            identifiants["arkeogis_id"] = str(extra["SITE_AKG_ID"])
        if extra.get("id_site"):
            identifiants["alsace_basel_id"] = str(extra["id_site"])

        precision = PrecisionLocalisation.CENTROIDE
        prec_raw = extra.get("precision_localisation")
        if prec_raw == "exact" or (x_l93 is not None and prec_raw != "centroïde"):
            precision = PrecisionLocalisation.EXACT
        elif prec_raw == "approx":
            precision = PrecisionLocalisation.APPROX

        pays_raw = extra.get("pays", "").upper()
        pays = {"DE": Pays.DE, "CH": Pays.CH}.get(pays_raw, Pays.FR)

        return Site(
            site_id=site_id,
            nom_site=record.commune or "Inconnu",
            variantes_nom=variantes,
            pays=pays,
            region_admin="Alsace",
            commune=commune,
            x_l93=x_l93,
            y_l93=y_l93,
            precision_localisation=precision,
            type_site=type_site,
            identifiants_externes=identifiants,
            phases=phases,
            sources=[source],
        )
