#!/usr/bin/env python3
"""Ingestion fine CAG 68 — notices communales (texte antiword).

Lit extracted_text.txt + communes.json, segmente les blocs sites, classifie
périodes (periodes.json) et types (types_sites.json), exporte CSV + rapport.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
REF_DIR = REPO_ROOT / "data" / "reference"

TEXT_PATH = SCRIPT_DIR / "extracted_text.txt"
COMMUNES_PATH = SCRIPT_DIR / "communes.json"
STATS_PATH = SCRIPT_DIR / "stats.json"
OUT_ALL = SCRIPT_DIR / "notices_sites.csv"
OUT_FER = SCRIPT_DIR / "notices_sites_fer.csv"
OUT_QUALITY = SCRIPT_DIR / "quality_report.json"

SOURCE_LABEL = "CAG 68 — Haut-Rhin (M. Zehner)"

# Ordre de spécificité décroissante (en cas de plusieurs types détectés)
TYPE_SPECIFICITY: list[str] = [
    "OPPIDUM",
    "SANCTUAIRE",
    "TUMULUS",
    "NECROPOLE",
    "DEPOT",
    "ATELIER",
    "HABITAT",
    "VOIE",
]

PROTOHIST_RE = re.compile(r"[Pp]rotohist(?:oire|orique)?")
BRONZE_FINAL_RE = re.compile(r"[Bb]ronze\s+final|BF\s*III")
NEOLITH_RE = re.compile(r"[Nn]éolith")
GALLO_ROM_RE = re.compile(r"[Gg]allo[- ]?romain|[ée]poque\s+romaine|[Rr]omaine?\b")
MEROV_RE = re.compile(r"[Mm]érovingi")
MEDIEV_RE = re.compile(r"[Mm]édiéval|[Mm]oyen\s+[âa]ge")

# Extensions sous-périodes texte (complément sub_period_regex JSON)
EXTRA_SUB_PERIOD_RES = [
    (re.compile(r"La\s+Tène\s*I\s*a?", re.I), "LT A"),
    (re.compile(r"La\s+Tène\s*I\s*b", re.I), "LT B1"),
    (re.compile(r"Hallstatt\s*C(?:\s*[-–/]\s*D\d?)?", re.I), "Ha C"),
    (re.compile(r"Hallstatt\s*D\s*1|Hallstatt\s*moyen\s*I", re.I), "Ha D1"),
    (re.compile(r"Hallstatt\s*D\s*2", re.I), "Ha D2"),
    (re.compile(r"Hallstatt\s*D\s*3", re.I), "Ha D3"),
    (re.compile(r"Hallstatt\s*D\b(?!\d)", re.I), "Ha D"),
]


def slugify(s: str, max_len: int = 48) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s or "x")[:max_len]


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_type_patterns(types_data: dict) -> list[tuple[str, re.Pattern[str]]]:
    """Alias FR triés par longueur décroissante (évite que 'voie' masque 'voie romaine')."""
    pairs: list[tuple[str, str]] = []
    for code, langs in types_data.get("aliases", {}).items():
        for phrase in langs.get("fr", []):
            pairs.append((code, phrase))
    pairs.sort(key=lambda x: len(x[1]), reverse=True)
    out: list[tuple[str, re.Pattern[str]]] = []
    for code, phrase in pairs:
        esc = re.escape(phrase)
        if phrase.endswith("e") and len(phrase) > 3:
            pat = rf"(?<![\wÀ-ÿ-]){esc}s?(?![\wÀ-ÿ-])"
        else:
            pat = rf"(?<![\wÀ-ÿ-]){esc}(?![\wÀ-ÿ-])"
        out.append((code, re.compile(pat, re.IGNORECASE)))
    return out


def compile_period_patterns(periodes: dict) -> list[tuple[str, re.Pattern[str]]]:
    out: list[tuple[str, re.Pattern[str]]] = []
    for key, spec in periodes.items():
        for p in spec.get("patterns_fr", []):
            out.append((key, re.compile(re.escape(p), re.IGNORECASE)))
    return out


def _fmt_num(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(v)
    return str(v)


def detect_periods(
    text: str,
    period_res: list[tuple[str, re.Pattern[str]]],
    sub_re: re.Pattern[str],
    periodes: dict,
) -> tuple[str, str, str | None, str | None, bool]:
    """periode normalisée, sous_période, datations, age_du_fer_relevant."""
    hall = latene = trans = False
    for key, rx in period_res:
        if not rx.search(text):
            continue
        if key == "HALLSTATT":
            hall = True
        elif key == "LA_TENE":
            latene = True
        elif key == "TRANSITION":
            trans = True
    if re.search(r"\bHa\s*[CD]\d?", text, re.I):
        hall = True
    if re.search(r"\bLT\s*[A-D]\d?|La\s+Tène|[Ll]aténi", text):
        latene = True
    if re.search(
        r"transition\s+Hallstatt|Ha\s*D3\s*/\s*LT|D3[-–]\s*La\s+Tène|charnière\s+Ha",
        text,
        re.I,
    ):
        trans = True
    proto = bool(PROTOHIST_RE.search(text))
    age_fer = hall or latene or trans or proto

    d0: Any = None
    d1: Any = None
    periode = ""
    if trans:
        periode = "TRANSITION"
        spec = periodes.get("TRANSITION", {})
        d0, d1 = spec.get("date_debut"), spec.get("date_fin")
    elif hall and latene:
        periode = "HALLSTATT_LA_TENE"
        d0, d1 = -800, -25
    elif hall:
        periode = "HALLSTATT"
        spec = periodes.get("HALLSTATT", {})
        d0, d1 = spec.get("date_debut"), spec.get("date_fin")
    elif latene:
        periode = "LA_TENE"
        spec = periodes.get("LA_TENE", {})
        d0, d1 = spec.get("date_debut"), spec.get("date_fin")
    elif proto:
        periode = "PROTOHISTOIRE"
        d0, d1 = None, None
    else:
        if BRONZE_FINAL_RE.search(text):
            periode = "BRONZE_FINAL"
        elif NEOLITH_RE.search(text):
            periode = "NEOLITHIQUE"
        elif GALLO_ROM_RE.search(text):
            periode = "GALLO_ROMAIN"
        elif MEROV_RE.search(text):
            periode = "MEROVINGIEN"
        elif MEDIEV_RE.search(text):
            periode = "MEDIEVAL"

    sous = ""
    m = sub_re.search(text)
    if m:
        sous = re.sub(r"\s+", "", m.group(0))
    for rx, label in EXTRA_SUB_PERIOD_RES:
        if rx.search(text):
            sous = label
            break

    if periode == "TRANSITION":
        sous = sous or "Ha D3 / LT A"
        d0, d1 = -500, -400

    if periode in ("HALLSTATT", "LA_TENE") and sous:
        subs = periodes.get(periode, {}).get("sous_periodes", {})
        if sous in subs:
            d0 = subs[sous]["date_debut"]
            d1 = subs[sous]["date_fin"]
    elif periode == "HALLSTATT_LA_TENE" and sous:
        for pk in ("HALLSTATT", "LA_TENE"):
            subs = periodes.get(pk, {}).get("sous_periodes", {})
            if sous in subs:
                d0 = subs[sous]["date_debut"]
                d1 = subs[sous]["date_fin"]
                break

    return periode, sous, _fmt_num(d0), _fmt_num(d1), age_fer


def pick_type_site(text: str, type_patterns: list[tuple[str, re.Pattern[str]]]) -> str:
    found: set[str] = set()
    for code, rx in type_patterns:
        if rx.search(text):
            found.add(code)
    if not found:
        return ""
    best = ""
    best_rank = 999
    rank = {c: i for i, c in enumerate(TYPE_SPECIFICITY)}
    for c in found:
        r = rank.get(c, 50)
        if r < best_rank:
            best_rank = r
            best = c
    return best


def extract_lieu_dit(text: str) -> str:
    m = re.search(
        r"(?:Aux\s+)?lieux?-dits?\s+([^.\n]+?)(?:\.|,|\n|$)",
        text,
        re.I,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())[:200]
    m2 = re.search(r"^Au\s+([^.\n\-–—]{4,80})", text.strip(), re.I)
    if m2:
        return re.sub(r"\s+", " ", m2.group(1).strip())
    return ""


BIBLIO_FALSE_COMMUNE = re.compile(
    r"\bpl\.\s*\d|\bfig\.\s*\d|M\.\s+Châtelet|;\s*-\s*[A-Z]\.",
    re.I,
)


def plausible_commune_title(name: str) -> bool:
    if len(name) > 72:
        return False
    if BIBLIO_FALSE_COMMUNE.search(name):
        return False
    return True


def split_communes_raw(text: str) -> list[tuple[str, str, str]]:
    """Liste de (numero, nom_ligne, corps_notice)."""
    lines = text.split("\n")
    header_re = re.compile(r"^(\d{3})\s*-\s*(.+)$")
    sections: list[tuple[str, str, list[str]]] = []
    current_num: str | None = None
    current_name: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current_num, current_name, buf
        if current_num is not None:
            sections.append((current_num, current_name or "", buf))
        buf = []

    for line in lines:
        m = header_re.match(line.strip())
        if m:
            nome = m.group(2).strip()
            if not plausible_commune_title(nome):
                if current_num is not None:
                    buf.append(line)
                continue
            flush()
            current_num, current_name = m.group(1), nome
            buf = []
        elif current_num is not None:
            buf.append(line)
    flush()
    return [(a, b, "\n".join(c).strip()) for a, b, c in sections]


# Début de bloc : "N* " optionnel ; refs (001, 002 AH) ou (004 AH, 005 AP) ; tiret ou espace + majuscule
BLOCK_START_RE = re.compile(
    r"(?m)^\s*(?:\d+\*\s*)?"
    r"(\((?:(?:\d{3}\s*,\s*)+\d{3}\s+(?:AH|AP|AE|AF)"
    r"|(?:\d{3}\s+(?:AH|AP|AE|AF)(?:\s*,\s*\d{3}\s+(?:AH|AP|AE|AF))*))\))"
    r"\s*(?:[-–—]\s+|\s+(?=[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜŸÇÆŒ«]))",
)


def parse_ref_tuple(full_paren: str) -> str:
    inner = re.sub(r"\s+", " ", full_paren.strip("()").strip())
    mb = re.match(
        r"^((?:\d{3}\s*,\s*)+)(\d{3})\s+(AH|AP|AE|AF)$",
        inner,
        re.I,
    )
    if mb:
        code = mb.group(3).upper()
        nums = re.findall(r"\d{3}", mb.group(1)) + [mb.group(2)]
        return "; ".join(f"{n} {code}" for n in nums)
    pairs = re.findall(r"(\d{3})\s+(AH|AP|AE|AF)", inner, re.I)
    if pairs:
        return "; ".join(f"{a} {b.upper()}" for a, b in pairs)
    return ""


def segment_blocks(body: str) -> list[tuple[str, str]]:
    """Liste de (ref_code, texte_bloc_complet incl. ref)."""
    matches = list(BLOCK_START_RE.finditer(body))
    if not matches:
        return []
    blocks: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end].strip()
        ref = parse_ref_tuple(m.group(1))
        blocks.append((ref, chunk))
    return blocks


def confidence(type_site: str, periode: str) -> str:
    has_t = bool(type_site)
    has_p = bool(periode)
    if has_t and has_p:
        return "HIGH"
    if has_t or has_p:
        return "MEDIUM"
    return "LOW"


def split_biblio(block: str) -> tuple[str, str]:
    """Heuristique : dernière portion avec citations 'p. ' ou ' ; - '."""
    if ";" not in block and "p." not in block.lower():
        return block, ""
    idx = block.rfind("\n\n")
    if idx > len(block) // 2 and idx > 0:
        desc, bib = block[:idx].strip(), block[idx:].strip()
        if re.search(r"\d{4}|p\.\s*\d", bib, re.I):
            return desc, bib
    return block, ""


def main() -> None:
    text = TEXT_PATH.read_text(encoding="utf-8")
    communes_meta = load_json(COMMUNES_PATH)
    stats_ref = load_json(STATS_PATH) if STATS_PATH.exists() else {}

    types_data = load_json(REF_DIR / "types_sites.json")
    periodes_data = load_json(REF_DIR / "periodes.json")

    periodes = periodes_data.get("periodes", {})
    sub_re_str = periodes_data.get(
        "sub_period_regex",
        r"(?:Ha\s*[CD](?:\d)?(?:-[CD]?\d)?|LT\s*[A-D](?:\d)?)",
    )
    sub_re = re.compile(sub_re_str, re.I)

    period_res = compile_period_patterns(periodes)
    type_patterns = build_type_patterns(types_data)

    meta_by_num: dict[str, dict] = {}
    for c in communes_meta:
        n = c["numero"]
        if n not in meta_by_num:
            meta_by_num[n] = c
    sections = split_communes_raw(text)

    rows: list[dict[str, Any]] = []
    communes_sans_bloc: list[str] = []
    communes_avec_bloc = 0
    refs_in_blocks = 0

    for numero, nom_ligne, body in sections:
        cmeta = meta_by_num.get(numero, {})
        commune = cmeta.get("nom", nom_ligne)
        blocks = segment_blocks(body)
        if not blocks and cmeta.get("nb_sites", 0) > 0:
            communes_sans_bloc.append(f"{numero} {commune}")
        if blocks:
            communes_avec_bloc += 1
        for ref_code, raw_block in blocks:
            refs_in_blocks += len([x for x in ref_code.split(";") if x.strip()])
            desc, biblio = split_biblio(raw_block)
            nom_cand = extract_lieu_dit(desc) or extract_lieu_dit(raw_block)
            if not nom_cand:
                nom_cand = re.sub(r"\s+", " ", desc[:120]).strip()

            periode, sous_periode, d0, d1, age_fer = detect_periods(
                raw_block, period_res, sub_re, periodes
            )
            type_site = pick_type_site(raw_block, type_patterns)
            conf = confidence(type_site, periode)

            site_id = f"CAG68_{slugify(commune)}_{short_hash(raw_block)}"

            rows.append(
                {
                    "site_id": site_id,
                    "nom_site": nom_cand,
                    "commune": commune,
                    "departement": "68",
                    "pays": "FR",
                    "type_site": type_site,
                    "longitude": "",
                    "latitude": "",
                    "x_l93": "",
                    "y_l93": "",
                    "periode": periode,
                    "sous_periode": sous_periode,
                    "datation_debut": d0 or "",
                    "datation_fin": d1 or "",
                    "confiance": conf,
                    "source": SOURCE_LABEL,
                    "description": desc,
                    "bibliographie": biblio,
                    "_ref_code": ref_code,
                    "_raw_block": raw_block,
                    "_age_du_fer_relevant": age_fer,
                }
            )

    csv_fields = [
        "site_id",
        "nom_site",
        "commune",
        "departement",
        "pays",
        "type_site",
        "longitude",
        "latitude",
        "x_l93",
        "y_l93",
        "periode",
        "sous_periode",
        "datation_debut",
        "datation_fin",
        "confiance",
        "source",
        "description",
        "bibliographie",
    ]

    for path in (OUT_ALL, OUT_FER):
        path.parent.mkdir(parents=True, exist_ok=True)

    with OUT_ALL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in csv_fields})

    fer_rows = [r for r in rows if r.get("_age_du_fer_relevant")]
    with OUT_FER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        w.writeheader()
        for r in fer_rows:
            w.writerow({k: r.get(k, "") for k in csv_fields})

    total_refs_stats = stats_ref.get("total_references_sites", 0)
    conf_counts: dict[str, int] = {}
    for r in rows:
        conf_counts[r["confiance"]] = conf_counts.get(r["confiance"], 0) + 1
    periode_counts: dict[str, int] = {}
    for r in rows:
        p = r["periode"] or "VIDE"
        periode_counts[p] = periode_counts.get(p, 0) + 1
    type_counts: dict[str, int] = {}
    for r in rows:
        t = r["type_site"] or "VIDE"
        type_counts[t] = type_counts.get(t, 0) + 1

    def sample_commune(num: str) -> dict[str, Any]:
        out_blocs = []
        for r in rows:
            if meta_by_num.get(num, {}).get("nom") != r["commune"]:
                continue
            out_blocs.append(
                {
                    "ref": r["_ref_code"],
                    "type_site": r["type_site"],
                    "periode": r["periode"],
                    "extrait": (r["description"][:180] + "…")
                    if len(r["description"]) > 180
                    else r["description"],
                }
            )
        return {"numero": num, "nom": meta_by_num.get(num, {}).get("nom"), "blocs": out_blocs}

    spot_001 = sample_commune("001")
    spot_066 = sample_commune("066")
    spot_152 = sample_commune("152")

    report = {
        "source_text": str(TEXT_PATH.relative_to(REPO_ROOT)),
        "script": "data/analysis/cag_68_texte/ingest.py",
        "total_blocs_sites": len(rows),
        "refs_comptees_dans_entetes_blocs": refs_in_blocks,
        "stats_json_total_references_sites": total_refs_stats,
        "note_comptage": "stats.json (analyze.py) déduplique les refs par commune et ne matche pas le format (001, 002 AH). ingest.py compte chaque ref listée dans l’en-tête de bloc ; le nombre de blocs et de refs peut être supérieur à 812.",
        "communes_total": len(sections),
        "communes_avec_au_moins_un_bloc": communes_avec_bloc,
        "communes_meta_avec_sites": stats_ref.get("communes_avec_sites", 0),
        "lignes_csv_fer": len(fer_rows),
        "taux_age_du_fer": round(len(fer_rows) / max(len(rows), 1), 4),
        "distribution_confiance": conf_counts,
        "distribution_periode": dict(sorted(periode_counts.items(), key=lambda x: -x[1])),
        "distribution_type_site": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "communes_avec_sites_sans_segmentation": communes_sans_bloc[:30],
        "spot_check_manuel": {
            "001_algolsheim": spot_001,
            "066_colmar": spot_066,
            "152_illfurth": spot_152,
        },
        "validation": {
            "algolsheim_refs_attendues_ordre": [
                "004 AH; 005 AP",
                "004 AP",
                "003 AP",
                "002 AH",
                "001 AH",
                "007 AH",
                "008 AH",
            ],
            "algolsheim_refs_extraites": [
                b[0]
                for b in segment_blocks(
                    next((b for n, _, b in sections if n == "001"), "")
                )
            ],
        },
    }

    OUT_QUALITY.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Blocs exportés : {len(rows)} → {OUT_ALL.name}")
    print(f"Âge du Fer (tagués) : {len(fer_rows)} → {OUT_FER.name}")
    print(f"Références dans entêtes de blocs : {refs_in_blocks} (stats.json : {total_refs_stats})")
    print(f"Rapport : {OUT_QUALITY.name}")


if __name__ == "__main__":
    main()
