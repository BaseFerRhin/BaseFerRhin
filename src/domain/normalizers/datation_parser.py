"""Unified datation parser for heterogeneous archaeological date formats.

Splits composite ranges into individual phases compatible with
``_VALID_SUB_PERIODS`` in ``src.domain.models.phase``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REFERENCE_PATH = Path(__file__).resolve().parents[3] / "data" / "reference" / "periodes.json"

_ARKEOGIS_RE = re.compile(r"^(-?\d+):(-?\d+)$")
_C14_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)(?:\s*(?:avant|av\.?)\s*(?:J\.?-?C\.?)?)?", re.IGNORECASE)
_PATRIARCHE_CHRONO_RE = re.compile(r"^EUR(FER|BRO|NEO|GAL|ROM|MED|MOD)[-]+$")
_TEXTUAL_AGE_RE = re.compile(
    r"[Aa]ge\s+du\s+(fer|bronze|Fer|Bronze)"
    r"(?:\s*[-–]\s*(?:[Aa]ge\s+du\s+)?(fer|bronze|Fer|Bronze|[Gg]allo[- ]?romain))?",
)

_SUB_PERIOD_RANGE_RE = re.compile(
    r"(Ha|LT)\s*([A-D]\d?)\s*[-–/]\s*(?:(Ha|LT)\s*)?([A-D]\d?)"
)
_SINGLE_SUB_RE = re.compile(r"(Ha|LT)\s*([A-D]\d?)")

_BOOL_COLUMN_MAP: dict[str, list[str]] = {
    "BF3_HaC": ["Ha C"],
    "HaD": ["Ha D"],
    "LTAB": ["LT A", "LT B"],
    "LTCD": ["LT C", "LT D"],
}


@dataclass(frozen=True)
class ParsedPhase:
    periode: str
    sous_periode: Optional[str]
    debut: Optional[int]
    fin: Optional[int]


class DatationParser:
    """Parse raw datation strings into validated phases."""

    def __init__(self, reference_path: Path = _REFERENCE_PATH) -> None:
        data = json.loads(reference_path.read_text(encoding="utf-8"))
        self._sub_dates: dict[str, tuple[int, int]] = {}
        self._period_bounds: dict[str, tuple[int, int]] = {}

        for period_key, info in data["periodes"].items():
            name = {
                "HALLSTATT": "Hallstatt",
                "LA_TENE": "La Tène",
                "TRANSITION": "Hallstatt/La Tène",
            }[period_key]
            self._period_bounds[name] = (info["date_debut"], info["date_fin"])
            for sub_name, sub_info in info["sous_periodes"].items():
                self._sub_dates[sub_name] = (sub_info["date_debut"], sub_info["date_fin"])

        self._expand_coarse = {
            "Ha C": ["Ha C"],
            "Ha D": ["Ha D1", "Ha D2", "Ha D3"],
            "LT A": ["LT A"],
            "LT B": ["LT B1", "LT B2"],
            "LT C": ["LT C1", "LT C2"],
            "LT D": ["LT D1", "LT D2"],
        }

    def _sub_to_periode(self, sub: str) -> str:
        if sub.startswith("Ha"):
            return "Hallstatt"
        if sub.startswith("LT"):
            return "La Tène"
        return "indéterminé"

    def _dates_for_sub(self, sub: str) -> tuple[Optional[int], Optional[int]]:
        if sub in self._sub_dates:
            return self._sub_dates[sub]
        if sub in self._expand_coarse:
            expanded = self._expand_coarse[sub]
            d0 = self._sub_dates.get(expanded[0], (None, None))[0]
            d1 = self._sub_dates.get(expanded[-1], (None, None))[1]
            return d0, d1
        return None, None

    def _resolve_sub(self, prefix: str, code: str) -> str:
        """Normalise a compact sub-period code like 'D1' to 'Ha D1'."""
        raw = f"{prefix} {code}"
        if raw in self._sub_dates or raw in self._expand_coarse:
            return raw
        coarse = f"{prefix} {code[0]}"
        if coarse in self._sub_dates or coarse in self._expand_coarse:
            return coarse
        return raw

    def parse(self, raw: str) -> list[ParsedPhase]:
        """Parse a raw datation string into a list of phases."""
        if not raw or raw.strip() in ("", "-", "Indéterminé", "indéterminé", "Non renseigné"):
            return [ParsedPhase("indéterminé", None, None, None)]

        text = raw.strip()

        if m := _ARKEOGIS_RE.match(text):
            return self._parse_arkeogis(int(m.group(1)), int(m.group(2)))

        if m := _PATRIARCHE_CHRONO_RE.match(text):
            return self._parse_patriarche_code(m.group(1))

        if m := _TEXTUAL_AGE_RE.search(text):
            return self._parse_textual_age(m.group(1), m.group(2))

        if m := _SUB_PERIOD_RANGE_RE.search(text):
            return self._parse_sub_range(m)

        if m := _SINGLE_SUB_RE.search(text):
            sub = self._resolve_sub(m.group(1), m.group(2))
            return self._expand_to_phases(sub)

        if m := _C14_RE.search(text):
            return self._parse_c14(int(m.group(1)), int(m.group(2)))

        return [ParsedPhase("indéterminé", None, None, None)]

    def parse_arkeogis_pair(self, start: str, end: str) -> list[ParsedPhase]:
        """Parse an ArkeoGIS STARTING_PERIOD + ENDING_PERIOD pair."""
        start_m = _ARKEOGIS_RE.match(start.strip()) if start else None
        end_m = _ARKEOGIS_RE.match(end.strip()) if end else None

        if start_m and end_m:
            debut = int(start_m.group(1))
            fin = int(end_m.group(2))
            return self._parse_arkeogis(debut, fin)

        return self.parse(start or end or "")

    def parse_boolean_columns(self, columns: dict[str, object]) -> list[ParsedPhase]:
        """Parse boolean period columns (BdD Proto Alsace format)."""
        phases: list[ParsedPhase] = []
        for col, sub_list in _BOOL_COLUMN_MAP.items():
            val = columns.get(col)
            if val and val not in (0, 0.0, "0", None, ""):
                for sub in sub_list:
                    phases.extend(self._expand_to_phases(sub))
        return phases or [ParsedPhase("indéterminé", None, None, None)]

    def _parse_arkeogis(self, debut: int, fin: int) -> list[ParsedPhase]:
        best_sub = None
        for sub_name, (d, f) in self._sub_dates.items():
            if d <= debut and fin <= f:
                if best_sub is None or (f - d) < (
                    self._sub_dates[best_sub][1] - self._sub_dates[best_sub][0]
                ):
                    best_sub = sub_name

        if best_sub:
            return [ParsedPhase(self._sub_to_periode(best_sub), best_sub, debut, fin)]

        periode = "indéterminé"
        for name, (d, f) in self._period_bounds.items():
            if d <= debut and fin <= f:
                periode = name
                break
            if debut <= f and fin >= d:
                periode = name
                break
        return [ParsedPhase(periode, None, debut, fin)]

    def _parse_patriarche_code(self, code: str) -> list[ParsedPhase]:
        mapping = {
            "FER": ("indéterminé", None, -800, -25),
            "BRO": ("indéterminé", None, -2200, -800),
            "GAL": ("La Tène", None, -450, -25),
            "ROM": ("indéterminé", None, -25, 500),
        }
        if code in mapping:
            p, s, d, f = mapping[code]
            return [ParsedPhase(p, s, d, f)]
        return [ParsedPhase("indéterminé", None, None, None)]

    def _parse_textual_age(self, age1: str, age2: Optional[str]) -> list[ParsedPhase]:
        a1 = age1.lower()
        a2 = age2.lower() if age2 else None

        if a1 == "fer" and not a2:
            return [ParsedPhase("indéterminé", None, -800, -25)]
        if a1 == "fer" and a2 and "gallo" in a2:
            return [ParsedPhase("La Tène", None, -450, -25)]
        if a1 == "bronze" and a2 and a2 == "fer":
            return [ParsedPhase("Hallstatt", None, -800, -450)]
        if a1 == "bronze" and not a2:
            return [ParsedPhase("indéterminé", None, -2200, -800)]

        return [ParsedPhase("indéterminé", None, None, None)]

    def _parse_sub_range(self, m: re.Match) -> list[ParsedPhase]:
        prefix1, code1, prefix2, code2 = m.group(1), m.group(2), m.group(3), m.group(4)
        if not prefix2:
            prefix2 = prefix1

        sub_start = self._resolve_sub(prefix1, code1)
        sub_end = self._resolve_sub(prefix2, code2)

        all_subs = list(self._sub_dates.keys())
        try:
            i_start = next(i for i, s in enumerate(all_subs) if s == sub_start or s.startswith(sub_start))
        except StopIteration:
            return self._expand_to_phases(sub_start) + self._expand_to_phases(sub_end)
        try:
            i_end = next(i for i in range(len(all_subs) - 1, -1, -1)
                         if all_subs[i] == sub_end or all_subs[i].startswith(sub_end))
        except StopIteration:
            return self._expand_to_phases(sub_start) + self._expand_to_phases(sub_end)

        if i_start > i_end:
            i_start, i_end = i_end, i_start

        phases: list[ParsedPhase] = []
        for sub in all_subs[i_start: i_end + 1]:
            d, f = self._sub_dates[sub]
            phases.append(ParsedPhase(self._sub_to_periode(sub), sub, d, f))
        return phases or [ParsedPhase("indéterminé", None, None, None)]

    def _expand_to_phases(self, sub: str) -> list[ParsedPhase]:
        if sub in self._expand_coarse:
            expanded = self._expand_coarse[sub]
            return [
                ParsedPhase(
                    self._sub_to_periode(s), s,
                    *self._sub_dates.get(s, (None, None))
                )
                for s in expanded
            ]
        d, f = self._dates_for_sub(sub)
        return [ParsedPhase(self._sub_to_periode(sub), sub, d, f)]

    def _parse_c14(self, val1: int, val2: int) -> list[ParsedPhase]:
        debut, fin = -max(val1, val2), -min(val1, val2)
        return self._parse_arkeogis(debut, fin)
