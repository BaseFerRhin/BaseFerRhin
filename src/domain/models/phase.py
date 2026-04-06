from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .enums import Periode


_VALID_SUB_PERIODS: dict[Periode, set[str]] = {
    Periode.HALLSTATT: {"Ha C", "Ha D", "Ha D1", "Ha D2", "Ha D3", "Ha D2-D3", "Ha D2/D3"},
    Periode.LA_TENE: {
        "LT A", "LT B", "LT B1", "LT B2",
        "LT C", "LT C1", "LT C2",
        "LT D", "LT D1", "LT D2",
    },
    Periode.TRANSITION: {"Ha D3 / LT A", "Ha D3/LT A"},
}


class PhaseOccupation(BaseModel):
    phase_id: str
    site_id: str
    periode: Periode
    sous_periode: Optional[str] = None
    datation_debut: Optional[int] = None
    datation_fin: Optional[int] = None
    methode_datation: Optional[str] = None
    mobilier_associe: list[str] = Field(default_factory=list)
    date_creation: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    date_maj: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def check_sub_period_consistency(self) -> "PhaseOccupation":
        if self.sous_periode is None:
            return self
        allowed = _VALID_SUB_PERIODS.get(self.periode, set())
        if allowed and self.sous_periode not in allowed:
            raise ValueError(
                f"Sous-période '{self.sous_periode}' incompatible "
                f"avec la période '{self.periode.value}'"
            )
        return self
