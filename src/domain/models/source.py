from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .enums import NiveauConfiance, TypeSource


class Source(BaseModel):
    source_id: str
    site_id: str
    reference: str
    type_source: Optional[TypeSource] = None
    url: Optional[str] = None
    ark_gallica: Optional[str] = None
    page_gallica: Optional[int] = None
    niveau_confiance: NiveauConfiance = NiveauConfiance.MOYEN
    confiance_ocr: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    date_extraction: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
