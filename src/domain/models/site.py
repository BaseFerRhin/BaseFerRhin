from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .enums import Pays, PrecisionLocalisation, StatutFouille, TypeSite
from .phase import PhaseOccupation
from .source import Source


class Site(BaseModel):
    site_id: str
    nom_site: str
    variantes_nom: list[str] = Field(default_factory=list)
    pays: Pays
    region_admin: str
    commune: str
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
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
