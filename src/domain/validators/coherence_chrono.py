from dataclasses import dataclass

from src.domain.models.enums import Periode
from src.domain.models.phase import PhaseOccupation

_PERIOD_RANGES: dict[Periode, tuple[int, int]] = {
    Periode.HALLSTATT: (-800, -450),
    Periode.LA_TENE: (-450, -25),
    Periode.TRANSITION: (-500, -400),
}

_VALID_SUB_PREFIXES: dict[Periode, list[str]] = {
    Periode.HALLSTATT: ["Ha"],
    Periode.LA_TENE: ["LT"],
    Periode.TRANSITION: ["Ha", "LT"],
}


@dataclass
class ValidationWarning:
    field: str
    message: str


def validate_chronology(phase: PhaseOccupation) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []

    if (
        phase.datation_debut is not None
        and phase.datation_fin is not None
        and phase.datation_debut > phase.datation_fin
    ):
        warnings.append(
            ValidationWarning("datation", "datation_debut > datation_fin")
        )

    period_range = _PERIOD_RANGES.get(phase.periode)
    if period_range:
        low, high = period_range
        if phase.datation_debut is not None and phase.datation_debut < low:
            warnings.append(
                ValidationWarning(
                    "datation_debut",
                    f"date {phase.datation_debut} antérieure à la plage {phase.periode.value} ({low})",
                )
            )
        if phase.datation_fin is not None and phase.datation_fin > high:
            warnings.append(
                ValidationWarning(
                    "datation_fin",
                    f"date {phase.datation_fin} postérieure à la plage {phase.periode.value} ({high})",
                )
            )

    if phase.sous_periode and phase.periode in _VALID_SUB_PREFIXES:
        valid_prefixes = _VALID_SUB_PREFIXES[phase.periode]
        if not any(phase.sous_periode.startswith(p) for p in valid_prefixes):
            warnings.append(
                ValidationWarning(
                    "sous_periode",
                    f"sous-période '{phase.sous_periode}' incompatible avec {phase.periode.value}",
                )
            )

    return warnings
