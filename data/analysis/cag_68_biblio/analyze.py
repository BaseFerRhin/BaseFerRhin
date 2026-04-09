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


def _extract_abbreviations_section(text: str) -> str:
    """Isolate the 'Abréviations et sigles utilisés' block (until Bibliographie)."""
    m = re.search(
        r"Abréviations et sigles utilisés\s*\r?\n(.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    block = m.group(1)
    end = re.search(r"\r?\n\s{8,}Bibliographie\s*\r?\n", block)
    if end:
        block = block[: end.start()]
    return block.strip()


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()


def _looks_like_abbrev_key(key: str) -> bool:
    """True if the text before ' : ' is a sigle / titre abrégé / titre court, not prose."""
    key = key.strip()
    if len(key) < 2 or len(key) > 130:
        return False
    if key[0].islower():
        return False
    low = key.lower()
    if low.startswith("cahiers d'") or low.startswith("devient "):
        return False
    # Long keys without multiple dotted tokens are usually prose, not list keys
    if len(key) > 100:
        return bool(
            re.search(
                r"(?:[A-ZÀ-Ÿ][a-zéèêàâîôùüö]*\.){2,}",
                key,
                re.UNICODE,
            )
        )
    # Abbreviated word tokens: Ann., Bull., Archéo., Nat., Ass., Sc., etc.
    if re.search(
        r"(?:[A-ZÀ-Ÿ][a-zéèêàâîôùüö]*\.|[A-Z]\.)+", key, re.UNICODE
    ):
        return True
    # Letter-dot-letter acronym blocks (B.A., R.A., Jh. R.G.Z.M. compact parts)
    compact = key.replace(" ", "")
    if re.match(r"^([A-Z]\.){2,}$", compact):
        return True
    # Short hyphenated titles (e.g. Mi Dorf - Mon village)
    if " - " in key and len(key) <= 70 and re.match(
        r"^[\w\s\-''’]+$", key, re.UNICODE
    ):
        return True
    # 1–4 word titles without medial dots: Gallia, Germania, Archéologia, Alsatia
    words = key.split()
    if 1 <= len(words) <= 5 and all(
        w and (w[0].isupper() or w[0].isdigit()) for w in words
    ):
        if len(words) <= 4 and not re.search(
            r"\b(de|du|des|la|le|les|et|pour|en|à|au|aux)\b", key.lower()
        ):
            return True
        # Allow "Gallia Préhistoire", "Etudes Celtiques", "Etudes Médiévales"
        if len(words) <= 3:
            return True
    return False


# Lines that start a new titre-seul entry after the previous physical line ended a bloc.
_STANDALONE_TITLE_PREFIXES: tuple[str, ...] = (
    "Alemannisches Jahrbuch",
    "Antiqua,",
    "Antiquités Nationales",
    "Archäologisches ",
    "Archéologia,",
    "Archéologie Suisse",
    "Bayerische Vorgeschichtsblätter",
    "Bericht über die Fortschritte",
    "Bull. de liaison des Professeurs",
    "Caesarodunum,",
    "Cahiers Archéologiques",
    "Chantiers d'",
    "Chroniques d'",
    "Dict. comm.",
    "Etudes Celtiques",
    "Etudes Médiévales",
    "Festschrift ",
    "Gallia Préhistoire",
    "Germania,",
    "Jahrbuch der Gesellschaft",
    "Jahrbuch des Geschichtsvereins",
    "Jahrbuch für Geschichte",
    "Journal de ",
    "Korrespondenzblatt",
    "Mannus-",
    "Mitteilungen der",
    "Prähistorische Zeitschrift",
    "Saarbrücker Beiträge",
    "Vie en Alsace",
    "Westdeutsche Zeitschrift",
    "Zeitschrift für Schweizerische",
)


def _colon_eol_title_key(key: str) -> bool:
    """Long titre-seul whose first line ends with ':' + newline only (ex. Jahrbuch… Munster)."""
    if len(key) > 200 or not key or not key[0].isupper():
        return False
    return bool(
        re.match(
            r"^(Jahrbuch\s|Chantiers d')",
            key,
            re.UNICODE | re.IGNORECASE,
        )
    )


def _prev_line_closes_block(prev: str) -> bool:
    p = prev.rstrip()
    if len(p) < 2:
        return False
    return p.endswith(").") or p.endswith(".") or p.endswith(".)")


def _flush_for_new_standalone_title(prev_line: str, line: str) -> bool:
    """True if *line* begins a new titre-seul entry after a completed previous line."""
    s = line.strip()
    if not s or s[0].islower():
        return False
    if not _prev_line_closes_block(prev_line):
        return False
    return any(s.startswith(pref) for pref in _STANDALONE_TITLE_PREFIXES)


def _infer_type(abbrev: str) -> str:
    a = abbrev.strip()
    if re.match(r"^([A-Z]\.){2,}\s*$", a.replace(" ", "")):
        return "sigle"
    if re.search(r"(?:[A-ZÀ-Ÿ]\.)+", a):
        return "abbreviation"
    return "title"


def _extract_cross_references(full_name: str) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"cf\.\s*([A-Za-z](?:[A-Za-z.]*)?)",
        full_name,
    ):
        r = _normalize_ws(m.group(1)).strip().rstrip(");")
        if r.endswith(","):
            r = r[:-1].strip()
        if not r or len(r) < 2 or "infra" in r.lower():
            continue
        if r not in seen:
            seen.add(r)
            refs.append(r)
    # "suite de …" — extraire uniquement un sigle du type A.B.C. si présent
    for m in re.finditer(
        r"suite\s+de\s+([^.;\n]+?)(?:\s*[;.]\s|\s*\(|$)",
        full_name,
        re.IGNORECASE,
    ):
        chunk = _normalize_ws(m.group(1))
        sm = re.search(r"(?:[A-Z]\.){2,}[A-Z]?(?:\.[A-Z])*\.?", chunk)
        if not sm:
            continue
        chunk = sm.group(0).rstrip()
        if chunk not in seen:
            seen.add(chunk)
            refs.append(chunk)
    # Parenthèses : (Ann. Soc. Hist. Sundgovienne), etc.
    for m in re.finditer(
        r"\(\s*((?:[A-ZÀ-Ÿ][a-zéèêàâîôùüö]*\.\s*){2,}[A-Za-zéèêàâîôùüö.\s\-]{1,80}?)\s*\)",
        full_name,
    ):
        inner = _normalize_ws(m.group(1)).rstrip(",.;")
        if len(inner) < 8 or len(inner) > 85:
            continue
        if inner not in seen:
            seen.add(inner)
            refs.append(inner)
    return refs


def _extract_location(full_name: str) -> str | None:
    # "..., Colmar, Alsatia." → ville d'édition, not imprint name
    m = re.search(
        r",\s*([A-Z][a-zéèêàâîôù]+(?:-[a-zéèêàâîôù]+)?)\s*,\s*(?:Alsatia|Alsagraphie)\s*\.\s*$",
        full_name,
    )
    if m:
        return m.group(1)
    # Trailing ", City." or ", City (depuis"
    m = re.search(
        r",\s*([A-Z][a-zéèêàâîôù]+(?:-[a-zéèêàâîôù]+)?)\s*\.\s*$",
        full_name,
    )
    if m:
        tail = m.group(1)
        if tail not in ("Alsatia", "Alsagraphie"):
            return tail
    m = re.search(
        r",\s*([A-Z][a-zéèêàâîôù]+(?:\s+[A-Z][a-zéèêàâîôù]+)?)\s*\(depuis",
        full_name,
    )
    if m:
        return m.group(1)
    m = re.search(
        r",\s*((?:Saint|Saint-)[\w\-]+(?:-en-[\w\-]+)?)\s*[.(]",
        full_name,
    )
    if m:
        return m.group(1)
    return None


def _extract_date_range(full_name: str) -> str | None:
    parts: list[str] = []
    for m in re.finditer(r"\((\d{4})\s*-\s*(\d{4})\)", full_name):
        parts.append(f"{m.group(1)}-{m.group(2)}")
    for m in re.finditer(r"\((\d{4})\s*-\s*(\d{1,4})\)", full_name):
        p = f"{m.group(1)}-{m.group(2)}"
        if p not in parts:
            parts.append(p)
    dep = re.findall(r"depuis\s+(\d{4})", full_name, re.IGNORECASE)
    tail = ""
    if dep:
        tail = f"depuis {dep[-1]}"
    if parts and tail:
        return f"{parts[0]}; {tail}"
    if parts:
        return parts[0]
    if tail:
        return tail
    return None


def _parse_abbrev_buffer(buf: list[str]) -> dict | None:
    if not buf:
        return None
    first = _normalize_ws(buf[0])
    rest_lines = [_normalize_ws(x) for x in buf[1:]]
    rest_joined = " ".join(x for x in rest_lines if x)

    m_colon = re.match(r"^(.+?)\s:\s+(.+)$", first)
    if m_colon and _looks_like_abbrev_key(m_colon.group(1)):
        key = _normalize_ws(m_colon.group(1))
        desc = _normalize_ws(m_colon.group(2) + (" " + rest_joined if rest_joined else ""))
        return _abbrev_record(key, desc)

    m_colon_eol = re.match(r"^(.+?)\s:\s*$", first)
    if m_colon_eol:
        key = _normalize_ws(m_colon_eol.group(1))
        desc = rest_joined
        if desc and (_looks_like_abbrev_key(key) or _colon_eol_title_key(key)):
            return _abbrev_record(key, desc)

    m_eq = re.match(r"^([^=]+)=\s*(.*)$", first)
    if m_eq and first.count("=") == 1:
        key = _normalize_ws(m_eq.group(1))
        if len(key) < 120 and key[0].isupper():
            desc = _normalize_ws(m_eq.group(2) + (" " + rest_joined if rest_joined else ""))
            return _abbrev_record(key, desc)

    full = _normalize_ws(" ".join(buf))
    if "," in full:
        abbrev = full.split(",", 1)[0].strip()
        abbrev = re.sub(r"\s*\(depuis[^)]*\)\s*$", "", abbrev, flags=re.IGNORECASE).strip()
    elif "." in full[:120]:
        abbrev = full.split(".", 1)[0].strip()
    else:
        abbrev = full[:72].strip()
    if len(abbrev) > 120:
        abbrev = abbrev[:117].rstrip() + "…"
    return _abbrev_record(abbrev, full)


def _abbrev_record(abbreviation: str, full_name: str) -> dict:
    cross = _extract_cross_references(full_name)
    loc = _extract_location(full_name)
    dr = _extract_date_range(full_name)
    return {
        "abbreviation": abbreviation,
        "full_name": full_name,
        "type": _infer_type(abbreviation),
        "cross_references": cross,
        "location": loc,
        "date_range": dr,
    }


def parse_abbreviations(text: str) -> list[dict]:
    """Extract abbreviation definitions: sigles, titres abrégés, titres complets, multi-lignes."""
    section = _extract_abbreviations_section(text)
    if not section:
        return []

    lines = section.splitlines()
    abbrevs: list[dict] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        rec = _parse_abbrev_buffer(buf)
        if rec:
            abbrevs.append(rec)
        buf = []

    for raw in lines:
        line = raw.replace("\u00a0", " ")
        s = line.strip()
        if not s:
            continue

        m_new = re.match(r"^(.+?)\s:\s+(.+)$", s)
        starts_with_key_colon = bool(
            m_new and _looks_like_abbrev_key(m_new.group(1))
        )
        m_eq_line = re.match(r"^([^=]+)=\s*(.*)$", s)
        starts_equals_title = bool(
            m_eq_line
            and s.count("=") == 1
            and len(m_eq_line.group(1).strip()) < 120
            and s[0].isupper()
        )

        if starts_with_key_colon or starts_equals_title:
            flush()
            buf.append(s)
            continue

        if buf and _flush_for_new_standalone_title(buf[-1], s):
            flush()
            buf.append(s)
            continue

        if not buf:
            buf.append(s)
            continue

        buf.append(s)

    flush()
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
