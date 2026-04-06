import json
from pathlib import Path

_REFERENCE_PATH = Path(__file__).resolve().parents[3] / "data" / "reference" / "toponymes_fr_de.json"


class ToponymeNormalizer:
    def __init__(self, reference_path: Path = _REFERENCE_PATH):
        data = json.loads(reference_path.read_text(encoding="utf-8"))
        self._canonical: dict[str, str] = {}
        self._all_variants: dict[str, list[str]] = {}

        for entry in data["concordance"]:
            canonical = entry["canonical"]
            variants = entry.get("variants", [])
            self._canonical[canonical.lower()] = canonical
            self._all_variants[canonical] = variants
            for v in variants:
                self._canonical[v.lower()] = canonical

    def normalize(self, toponym: str) -> tuple[str, list[str]]:
        """Return (canonical_name, other_variants_to_store)."""
        key = toponym.strip().lower()
        if key not in self._canonical:
            return toponym.strip(), []

        canonical = self._canonical[key]
        variants = []
        if toponym.strip() != canonical:
            variants.append(toponym.strip())
        return canonical, variants

    def get_variants(self, canonical: str) -> list[str]:
        return self._all_variants.get(canonical, [])
