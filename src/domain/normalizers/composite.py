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
        if record.latitude_raw is not None and record.longitude_raw is not None:
            x_l93, y_l93 = wgs84_to_l93(record.longitude_raw, record.latitude_raw)

        return Site(
            site_id=site_id,
            nom_site=record.commune or "Inconnu",
            variantes_nom=variantes,
            pays=Pays.FR,
            region_admin="Alsace",
            commune=commune,
            x_l93=x_l93,
            y_l93=y_l93,
            precision_localisation=(
                PrecisionLocalisation.EXACT
                if x_l93 is not None
                else PrecisionLocalisation.CENTROIDE
            ),
            type_site=type_site,
            phases=phases,
            sources=[source],
        )
