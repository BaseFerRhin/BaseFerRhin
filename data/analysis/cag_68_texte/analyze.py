#!/usr/bin/env python3
"""Extraction et analyse structurée de cag_68_texte.doc (CAG Haut-Rhin).

Utilise antiword pour convertir le .doc legacy, puis parse les notices
communales et les entrées de sites archéologiques.

Produit :
  - extracted_text.txt  : texte brut complet
  - communes.json       : liste des notices communales avec sites extraits
  - metadata.json       : metadata enrichie (remplace le stub)
  - stats.json          : statistiques globales
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR.parents[1] / "input" / "cag_68_texte.doc"

PERIOD_PATTERNS = {
    "Néolithique": r"[Nn]éolithique",
    "Bronze ancien": r"[Bb]ronze\s+ancien",
    "Bronze moyen": r"[Bb]ronze\s+moyen",
    "Bronze final": r"[Bb]ronze\s+final|BF\s*III",
    "Hallstatt": r"[Hh]allstatt|Ha\s*[A-D]\d?",
    "La Tène": r"[Ll]a\s+[Tt]ène|[Ll]aténi|LT\s*[A-D]",
    "Protohistoire": r"[Pp]rotohist",
    "Gallo-romain": r"[Gg]allo.?romain|[Rr]omain",
    "Mérovingien": r"[Mm]érovingi",
    "Médiéval": r"[Mm]édiéval|[Mm]oyen\s+[AÂ]ge",
}

TYPE_PATTERNS = {
    "tumulus": r"[Tt]umulus|[Tt]ertre",
    "nécropole": r"[Nn]écropole|[Cc]imetière|[Ss]épulture|[Ii]nhumation",
    "habitat": r"[Hh]abitat|[Mm]aison|[Ff]onde?\s+de\s+cabane",
    "oppidum": r"[Oo]ppidum|[Ee]nceinte|[Ff]ortifi",
    "voie": r"[Vv]oie\s+romaine|[Rr]oute|[Cc]hemin",
    "villa": r"[Vv]illa",
    "four": r"[Ff]our|[Ff]ourneau|[Ff]oyer",
    "dépôt": r"[Dd]épôt|[Cc]ache|[Tt]résor",
    "silo": r"[Ss]ilo",
    "fossé": r"[Ff]ossé|[Ee]nclos",
    "sanctuaire": r"[Ss]anctuaire|[Tt]emple|[Ll]ieu\s+de\s+culte",
    "motte": r"[Mm]otte|[Cc]hâteau",
    "atelier": r"[Aa]telier|[Ff]orge|[Mm]étallurg",
    "menhir": r"[Mm]enhir|[Ss]tèle",
}


def extract_text() -> str:
    result = subprocess.run(
        ["antiword", str(INPUT_FILE)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"antiword failed: {result.stderr}")
    return result.stdout


def parse_communes(text: str) -> list[dict]:
    lines = text.split("\n")
    commune_pattern = re.compile(r"^(\d{3})\s*-\s*(.+)$")
    site_ref_pattern = re.compile(r"\((\d{3})\s+(AH|AP|AE|AF)\)")

    communes: list[dict] = []
    current: dict | None = None
    current_text_lines: list[str] = []

    for line in lines:
        m = commune_pattern.match(line.strip())
        if m:
            if current:
                current["text"] = "\n".join(current_text_lines).strip()
                _enrich_commune(current)
                communes.append(current)

            current = {
                "numero": m.group(1),
                "nom": m.group(2).strip(),
                "sites": [],
            }
            current_text_lines = []
        elif current is not None:
            current_text_lines.append(line)
            for sm in site_ref_pattern.finditer(line):
                ref = f"{sm.group(1)} {sm.group(2)}"
                if ref not in [s["ref"] for s in current["sites"]]:
                    current["sites"].append({"ref": ref, "type_code": sm.group(2)})

    if current:
        current["text"] = "\n".join(current_text_lines).strip()
        _enrich_commune(current)
        communes.append(current)

    return communes


def _enrich_commune(commune: dict) -> None:
    text = commune.get("text", "")

    periods_found = []
    for period, pattern in PERIOD_PATTERNS.items():
        if re.search(pattern, text):
            periods_found.append(period)
    commune["periodes_mentionnees"] = periods_found

    types_found = []
    for site_type, pattern in TYPE_PATTERNS.items():
        if re.search(pattern, text):
            types_found.append(site_type)
    commune["types_mentionnes"] = types_found

    commune["nb_sites"] = len(commune["sites"])
    commune["longueur_texte"] = len(text)

    commune.pop("text", None)


def compute_stats(communes: list[dict]) -> dict:
    total_sites = sum(c["nb_sites"] for c in communes)
    all_periods: Counter = Counter()
    all_types: Counter = Counter()
    type_codes: Counter = Counter()

    for c in communes:
        for p in c["periodes_mentionnees"]:
            all_periods[p] += 1
        for t in c["types_mentionnes"]:
            all_types[t] += 1
        for s in c["sites"]:
            type_codes[s["type_code"]] += 1

    communes_with_sites = [c for c in communes if c["nb_sites"] > 0]
    top_communes = sorted(communes, key=lambda c: c["nb_sites"], reverse=True)[:20]

    return {
        "total_communes": len(communes),
        "communes_avec_sites": len(communes_with_sites),
        "communes_sans_site": len(communes) - len(communes_with_sites),
        "total_references_sites": total_sites,
        "type_codes": dict(type_codes.most_common()),
        "periodes_frequence": dict(all_periods.most_common()),
        "types_frequence": dict(all_types.most_common()),
        "top_20_communes": [
            {"numero": c["numero"], "nom": c["nom"], "nb_sites": c["nb_sites"]}
            for c in top_communes
        ],
        "longueur_moyenne_notice": round(
            sum(c["longueur_texte"] for c in communes) / max(len(communes), 1)
        ),
    }


def build_metadata(stats: dict, text_len: int) -> dict:
    age_fer_communes = []
    return {
        "file_name": "cag_68_texte.doc",
        "file_path": "data/input/cag_68_texte.doc",
        "format": "DOC",
        "file_size_kb": INPUT_FILE.stat().st_size // 1024,
        "extraction_tool": "antiword",
        "total_lines_extracted": text_len,
        "source": {
            "file_name": "cag_68_texte.doc",
            "platform": "Carte Archéologique de la Gaule — Haut-Rhin (68)",
            "auteur": "M. Zehner",
            "type": "Notices communales archéologiques",
        },
        "structure": {
            "type": "Notices communales numérotées (001–NNN)",
            "pattern": "NNN - NomCommune",
            "references_internes": "NNN AH/AP/AE/AF",
        },
        "statistics": stats,
        "geographic": {
            "departement": "68 — Haut-Rhin",
            "region": "Alsace",
            "coordinates": "Aucune coordonnée dans le texte",
        },
        "quality": {
            "confidence_level": "MEDIUM",
            "issues": [
                "Format .doc legacy — extraction via antiword",
                "Pas de coordonnées géographiques",
                "Texte non structuré nécessitant NER pour extraction fine",
            ],
        },
    }


def main() -> None:
    print("Extraction du texte avec antiword...")
    text = extract_text()
    text_path = SCRIPT_DIR / "extracted_text.txt"
    text_path.write_text(text, encoding="utf-8")
    print(f"  Texte extrait : {len(text)} caractères, {text.count(chr(10))} lignes")

    print("Parsing des notices communales...")
    communes = parse_communes(text)
    print(f"  {len(communes)} communes trouvées")

    communes_path = SCRIPT_DIR / "communes.json"
    communes_path.write_text(
        json.dumps(communes, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("Calcul des statistiques...")
    stats = compute_stats(communes)

    stats_path = SCRIPT_DIR / "stats.json"
    stats_path.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    metadata = build_metadata(stats, text.count("\n"))
    meta_path = SCRIPT_DIR / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nRésultats :")
    print(f"  Communes : {stats['total_communes']}")
    print(f"  Communes avec sites : {stats['communes_avec_sites']}")
    print(f"  Références de sites : {stats['total_references_sites']}")
    print(f"  Codes type : {stats['type_codes']}")
    print(f"  Périodes les plus fréquentes : {dict(list(stats['periodes_frequence'].items())[:5])}")
    print(f"  Types les plus fréquents : {dict(list(stats['types_frequence'].items())[:5])}")
    print(f"\nFichiers générés :")
    for f in [text_path, communes_path, stats_path, meta_path]:
        print(f"  {f.relative_to(SCRIPT_DIR)} ({f.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
