from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .enums import Pays, PrecisionLocalisation, StatutFouille, TypeSite
from .phase import PhaseOccupation
from .source import Source

# Lambert-93 (EPSG:2154) bounds for metropolitan France
_X_L93_MIN, _X_L93_MAX = 100_000.0, 1_200_000.0
_Y_L93_MIN, _Y_L93_MAX = 6_000_000.0, 7_200_000.0


class Site(BaseModel):
    site_id: str
    nom_site: str
    variantes_nom: list[str] = Field(default_factory=list)
    pays: Pays
    region_admin: str
    commune: str
    x_l93: Optional[float] = Field(default=None, ge=_X_L93_MIN, le=_X_L93_MAX)
    y_l93: Optional[float] = Field(default=None, ge=_Y_L93_MIN, le=_Y_L93_MAX)
    precision_localisation: PrecisionLocalisation
    type_site: TypeSite
    description: Optional[str] = None
    surface_m2: Optional[float] = Field(default=None, ge=0)
    altitude_m: Optional[float] = None
    statut_fouille: Optional[StatutFouille] = None
    identifiants_externes: dict[str, str] = Field(default_factory=dict)
    commentaire_qualite: Optional[str] = None
    phases: list[PhaseOccupation] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    date_creation: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    date_maj: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
