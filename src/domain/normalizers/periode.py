import json
import re
from pathlib import Path
from typing import Optional

from src.domain.models.enums import Periode

_REFERENCE_PATH = Path(__file__).resolve().parents[3] / "data" / "reference" / "periodes.json"


class PeriodeNormalizer:
    def __init__(self, reference_path: Path = _REFERENCE_PATH):
        data = json.loads(reference_path.read_text(encoding="utf-8"))
        self._patterns: dict[Periode, list[str]] = {}
        self._sub_period_regex = re.compile(data["sub_period_regex"])

        for code, info in data["periodes"].items():
            periode = Periode[code]
            self._patterns[periode] = info["patterns_fr"] + info["patterns_de"]

    def normalize(self, raw_text: str) -> tuple[Periode, Optional[str]]:
        sub_match = self._sub_period_regex.search(raw_text)
        sub_period = sub_match.group(0) if sub_match else None

        for periode, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.lower() in raw_text.lower():
                    return periode, sub_period

        if sub_period:
            if sub_period.startswith("Ha"):
                return Periode.HALLSTATT, sub_period
            if sub_period.startswith("LT"):
                return Periode.LA_TENE, sub_period

        return Periode.INDETERMINE, None
