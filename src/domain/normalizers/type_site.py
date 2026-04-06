import json
from pathlib import Path

from src.domain.models.enums import TypeSite

_REFERENCE_PATH = Path(__file__).resolve().parents[3] / "data" / "reference" / "types_sites.json"


class TypeSiteNormalizer:
    def __init__(self, reference_path: Path = _REFERENCE_PATH):
        data = json.loads(reference_path.read_text(encoding="utf-8"))
        self._lookup: dict[str, TypeSite] = {}
        for type_code, lang_aliases in data["aliases"].items():
            ts = TypeSite[type_code]
            for aliases in lang_aliases.values():
                for alias in aliases:
                    self._lookup[alias.lower()] = ts
        self._unrecognized: list[str] = []

    def normalize(self, raw_text: str) -> TypeSite:
        text_lower = raw_text.strip().lower()
        if text_lower in self._lookup:
            return self._lookup[text_lower]
        for alias, ts in self._lookup.items():
            if alias in text_lower:
                return ts
        self._unrecognized.append(raw_text)
        return TypeSite.INDETERMINE

    @property
    def unrecognized_terms(self) -> list[str]:
        return list(self._unrecognized)
