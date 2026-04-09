#!/usr/bin/env python3
"""Extraction et analyse structurée de cag_68_biblio.doc (Bibliographie CAG 68).

Parse la bibliographie : section abréviations + entrées auteur-année.

Produit :
  - extracted_text.txt    : texte brut
  - abbreviations.json    : abréviations de revues/institutions
  - biblio_entries.json   : entrées bibliographiques structurées
  - metadata.json         : metadata enrichie
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR.parents[1] / "input" / "cag_68_biblio.doc"


def extract_text() -> str:
    result = subprocess.run(
        ["antiword", str(INPUT_FILE)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"antiword failed: {result.stderr}")
    return result.stdout


def parse_abbreviations(text: str) -> list[dict]:
    """Extract abbreviation definitions from the first section."""
    abbrevs: list[dict] = []
    pattern = re.compile(
        r"^([A-Z][A-Z.\s]+[A-Z.])\s*:\s*(.+)",
        re.MULTILINE
    )
    for m in pattern.finditer(text[:8000]):
        abbrevs.append({
            "abbreviation": m.group(1).strip(),
            "full_name": m.group(2).strip()[:200],
        })
    return abbrevs


def parse_biblio_entries(text: str) -> list[dict]:
    """Extract bibliography entries (Author, year = title pattern)."""
    entries: list[dict] = []

    author_pattern = re.compile(r"^([A-Z][a-zéèêàâîôùüö]+(?:\s+[A-Z]\.(?:-[A-Z]\.)?)?(?:\s+et\s+(?:alii|[a-z]+))?),?\s*$", re.MULTILINE)
    year_pattern = re.compile(r"^(\d{4}[a-z]?)\s*=\s*(.+)")

    lines = text.split("\n")
    current_author: str | None = None
    current_line_buf = ""

    for line in lines:
        stripped = line.strip()

        am = author_pattern.match(stripped)
        if am:
            current_author = am.group(1).rstrip(",")
            current_line_buf = ""
            continue

        if current_author and stripped:
            current_line_buf += " " + stripped if current_line_buf else stripped

            ym = year_pattern.match(current_line_buf.strip())
            if ym:
                year_str = ym.group(1)
                title = ym.group(2).strip()

                year_num = None
                ym2 = re.match(r"(\d{4})", year_str)
                if ym2:
                    year_num = int(ym2.group(1))

                pages = None
                pm = re.search(r"(\d+)\s*p\.", title)
                if pm:
                    pages = int(pm.group(1))

                entries.append({
                    "author": current_author,
                    "year_raw": year_str,
                    "year": year_num,
                    "title_fragment": title[:300],
                    "pages": pages,
                })
                current_line_buf = ""

        if not stripped:
            current_line_buf = ""

    return entries


def compute_stats(entries: list[dict], abbrevs: list[dict]) -> dict:
    authors: Counter = Counter()
    years: Counter = Counter()
    decades: Counter = Counter()

    for e in entries:
        authors[e["author"]] += 1
        if e["year"]:
            years[e["year"]] += 1
            decades[e["year"] // 10 * 10] += 1

    return {
        "total_entries": len(entries),
        "total_abbreviations": len(abbrevs),
        "unique_authors": len(authors),
        "top_20_authors": dict(authors.most_common(20)),
        "year_range": {
            "min": min((e["year"] for e in entries if e["year"]), default=None),
            "max": max((e["year"] for e in entries if e["year"]), default=None),
        },
        "entries_by_decade": dict(sorted(decades.items())),
        "entries_with_pages": sum(1 for e in entries if e["pages"]),
    }


def main() -> None:
    print("Extraction du texte avec antiword...")
    text = extract_text()
    text_path = SCRIPT_DIR / "extracted_text.txt"
    text_path.write_text(text, encoding="utf-8")
    print(f"  {len(text)} caractères, {text.count(chr(10))} lignes")

    print("Parsing des abréviations...")
    abbrevs = parse_abbreviations(text)
    print(f"  {len(abbrevs)} abréviations trouvées")
    abbrev_path = SCRIPT_DIR / "abbreviations.json"
    abbrev_path.write_text(
        json.dumps(abbrevs, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("Parsing des entrées bibliographiques...")
    entries = parse_biblio_entries(text)
    print(f"  {len(entries)} entrées trouvées")
    entries_path = SCRIPT_DIR / "biblio_entries.json"
    entries_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    stats = compute_stats(entries, abbrevs)

    metadata = {
        "file_name": "cag_68_biblio.doc",
        "file_path": "data/input/cag_68_biblio.doc",
        "format": "DOC",
        "file_size_kb": INPUT_FILE.stat().st_size // 1024,
        "extraction_tool": "antiword",
        "total_lines_extracted": text.count("\n"),
        "source": {
            "file_name": "cag_68_biblio.doc",
            "platform": "Carte Archéologique de la Gaule — Haut-Rhin (68)",
            "auteur": "M. Zehner",
            "type": "Bibliographie",
        },
        "structure": {
            "type": "Bibliographie académique",
            "sections": ["Abréviations et sigles", "Références par auteur"],
            "entry_pattern": "Auteur X.,\\nANNEE = Titre...",
        },
        "statistics": stats,
        "quality": {
            "confidence_level": "MEDIUM",
            "issues": [
                "Format .doc legacy — extraction via antiword",
                "Certaines entrées multi-lignes mal jointes",
                "Entrées collectives (et alii) parfois mal parsées",
            ],
        },
    }

    meta_path = SCRIPT_DIR / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nStatistiques :")
    print(f"  Entrées bib. : {stats['total_entries']}")
    print(f"  Auteurs uniques : {stats['unique_authors']}")
    print(f"  Période couverte : {stats['year_range']}")
    print(f"  Top 5 auteurs : {dict(list(stats['top_20_authors'].items())[:5])}")

    print(f"\nFichiers générés :")
    for f in [text_path, abbrev_path, entries_path, meta_path]:
        print(f"  {f.name} ({f.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
