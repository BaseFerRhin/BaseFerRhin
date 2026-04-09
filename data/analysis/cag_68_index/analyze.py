#!/usr/bin/env python3
"""Extraction et analyse structurée de cag_68_index.doc (Index CAG 68).

Parse l'index alphabétique qui référence des objets, types de sites et
concepts archéologiques avec renvois vers les notices communales (numéros).

Produit :
  - extracted_text.txt  : texte brut
  - index_entries.json  : entrées structurées (terme → communes référencées)
  - metadata.json       : metadata enrichie
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR.parents[1] / "input" / "cag_68_index.doc"


def extract_text() -> str:
    result = subprocess.run(
        ["antiword", str(INPUT_FILE)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"antiword failed: {result.stderr}")
    return result.stdout


def parse_index(text: str) -> list[dict]:
    """Parse index entries like 'terme : NNN (details), NNN (details), ...'

    Handles antiword line wrapping where all lines start at column 0.
    A NEW entry is detected when the line contains ' : ' and the part before
    it looks like an index term (letters, spaces, parentheticals) while the
    part after starts with a 3-digit commune number.
    """
    lines = text.split("\n")

    entry_start_re = re.compile(
        r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,\-\'()«»]+?)\s*:\s*(\d{3}.*)"
    )
    header_re = re.compile(r"^\s*-\s*[A-Z]\s*-\s*$")
    skip_re = re.compile(r"^\s*Index alphabétique|^\s*68\s+Haut-Rhin\s*$|^\s*$")

    raw_entries: list[tuple[str, str]] = []
    current_term = ""
    current_refs = ""

    for line in lines:
        stripped = line.strip()
        if not stripped or header_re.match(stripped) or skip_re.match(stripped):
            continue

        m = entry_start_re.match(stripped)
        if m:
            if current_term:
                raw_entries.append((current_term, current_refs))
            current_term = m.group(1).strip()
            current_refs = m.group(2).strip()
        elif current_term:
            current_refs += " " + stripped

    if current_term:
        raw_entries.append((current_term, current_refs))

    entries: list[dict] = []
    ref_pattern = re.compile(r"\b(\d{3})\b")

    for terme, refs_text in raw_entries:
        commune_nums = sorted(set(ref_pattern.findall(refs_text)))

        cross_refs = []
        for cm in re.finditer(r"cf\.?\s+(?:aussi\s+|surtout\s+)?([a-zéèêàâîôùüö\s,]+)", refs_text, re.IGNORECASE):
            cross_refs.append(cm.group(1).strip().rstrip(","))

        if commune_nums:
            entries.append({
                "terme": terme,
                "communes_ref": commune_nums,
                "nb_refs": len(commune_nums),
                "cross_refs": cross_refs if cross_refs else None,
            })

    return entries


def categorize_entries(entries: list[dict]) -> dict[str, list[str]]:
    """Group index terms into archaeological categories."""
    categories: dict[str, list[str]] = {
        "mobilier": [],
        "structure": [],
        "période": [],
        "matériau": [],
        "activité": [],
        "funéraire": [],
        "voirie": [],
        "autre": [],
    }

    mobilier_kw = ["fibule", "bracelet", "anneau", "épée", "lance", "céramique",
                    "amphore", "vase", "perle", "monnaie", "hache", "couteau",
                    "agrafe", "arme", "applique", "boucle", "clou", "aiguille"]
    structure_kw = ["mur", "four", "fossé", "silo", "cave", "fosse", "puits",
                    "fondation", "sol", "aire", "enclos", "palissade"]
    period_kw = ["hallstatt", "tène", "bronze", "néolith", "romain", "méroving",
                 "médiéval", "antiq"]
    material_kw = ["bronze", "fer", "or", "argent", "verre", "os", "silex",
                   "lignite", "ambre", "argile"]
    funerary_kw = ["tombe", "tumulus", "nécropole", "sépulture", "inhumation",
                   "crémation", "urne", "sarcophage", "squelette"]
    road_kw = ["voie", "route", "chemin", "pont", "aqueduc", "borne"]

    for entry in entries:
        t = entry["terme"].lower()
        if any(kw in t for kw in funerary_kw):
            categories["funéraire"].append(entry["terme"])
        elif any(kw in t for kw in mobilier_kw):
            categories["mobilier"].append(entry["terme"])
        elif any(kw in t for kw in structure_kw):
            categories["structure"].append(entry["terme"])
        elif any(kw in t for kw in period_kw):
            categories["période"].append(entry["terme"])
        elif any(kw in t for kw in material_kw):
            categories["matériau"].append(entry["terme"])
        elif any(kw in t for kw in road_kw):
            categories["voirie"].append(entry["terme"])
        else:
            categories["autre"].append(entry["terme"])

    return {k: v for k, v in categories.items() if v}


def compute_stats(entries: list[dict]) -> dict:
    all_communes: Counter = Counter()
    for e in entries:
        for c in e["communes_ref"]:
            all_communes[c] += 1

    top_by_refs = sorted(entries, key=lambda e: e["nb_refs"], reverse=True)[:20]

    return {
        "total_entries": len(entries),
        "total_commune_references": sum(e["nb_refs"] for e in entries),
        "communes_distinctes_referenciees": len(all_communes),
        "top_20_communes_citees": dict(all_communes.most_common(20)),
        "top_20_termes_par_refs": [
            {"terme": e["terme"], "nb_refs": e["nb_refs"]} for e in top_by_refs
        ],
    }


def main() -> None:
    print("Extraction du texte avec antiword...")
    text = extract_text()
    text_path = SCRIPT_DIR / "extracted_text.txt"
    text_path.write_text(text, encoding="utf-8")
    print(f"  {len(text)} caractères, {text.count(chr(10))} lignes")

    print("Parsing de l'index...")
    entries = parse_index(text)
    print(f"  {len(entries)} entrées trouvées")

    categories = categorize_entries(entries)
    for cat, terms in categories.items():
        print(f"    {cat}: {len(terms)} termes")

    entries_path = SCRIPT_DIR / "index_entries.json"
    entries_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    stats = compute_stats(entries)

    metadata = {
        "file_name": "cag_68_index.doc",
        "file_path": "data/input/cag_68_index.doc",
        "format": "DOC",
        "file_size_kb": INPUT_FILE.stat().st_size // 1024,
        "extraction_tool": "antiword",
        "total_lines_extracted": text.count("\n"),
        "source": {
            "file_name": "cag_68_index.doc",
            "platform": "Carte Archéologique de la Gaule — Haut-Rhin (68)",
            "auteur": "M. Zehner",
            "type": "Index alphabétique thématique",
        },
        "structure": {
            "type": "Index alphabétique par terme archéologique",
            "pattern": "terme : NNN (détails), NNN (détails)",
            "sections": "A-Z",
        },
        "statistics": stats,
        "categories": {k: len(v) for k, v in categories.items()},
        "quality": {
            "confidence_level": "MEDIUM",
            "issues": [
                "Format .doc legacy — extraction via antiword",
                "Jointure de lignes multi-lignes imparfaite",
                "Certaines entrées mal parsées à cause du wrapping",
            ],
        },
    }

    meta_path = SCRIPT_DIR / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nStatistiques :")
    print(f"  Entrées d'index : {stats['total_entries']}")
    print(f"  Références totales : {stats['total_commune_references']}")
    print(f"  Communes distinctes : {stats['communes_distinctes_referenciees']}")

    print(f"\nFichiers générés :")
    for f in [text_path, entries_path, meta_path]:
        print(f"  {f.name} ({f.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
