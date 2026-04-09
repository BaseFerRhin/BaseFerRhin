#!/usr/bin/env python3
"""Pipeline d'ingestion — BdD_Proto_Alsace (1).xlsx → sites_cleaned.csv + quality_report.json."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

import pandas as pd

try:
    from pyproj import Transformer
except ImportError as e:  # pragma: no cover
    raise SystemExit("Install pyproj: pip install pyproj") from e

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None  # type: ignore
    process = None  # type: ignore

ROOT = Path(__file__).resolve().parents[2].parent
ANALYSIS_DIR = Path(__file__).resolve().parent

PROTO_XLSX = ROOT / "data" / "input" / "BdD_Proto_Alsace (1).xlsx"
ALSACE_AF_XLSX = ROOT / "data" / "input" / "Alsace_Basel_AF (1).xlsx"
PATRIARCHE_XLSX = ROOT / "data" / "input" / "20250806_Patriarche_ageFer.xlsx"
REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
GOLDEN_CSV = ROOT / "data" / "sources" / "golden_sites.csv"
EXISTING_CLEANED = ROOT / "data" / "output" / "sites_cleaned.csv"

OUT_CSV = ANALYSIS_DIR / "sites_cleaned.csv"
OUT_REPORT = ANALYSIS_DIR / "quality_report.json"

SOURCE_LABEL = "BdD_Proto_Alsace_xlsx"
FLAG_COLS = ["BA", "BM", "BF1", "BF2", "BF3_HaC", "HaD", "LTAB", "LTCD"]
FER_FLAG_COLS = ["LTAB", "LTCD", "HaD", "BF3_HaC"]
STRIP_COLS = ["commune", "lieu_dit", "datation_1", "datation_2", "biblio", "structures", "rq"]
DROP_COLS = ["type_precision", "conservati"]


def _nfkc_lower(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    return s.strip().lower()


def normalize_place(s: Any) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = _nfkc_lower(str(s))
    return re.sub(r"\s+", " ", t)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_flat_type_tokens(types_ref: dict) -> dict[str, set[str]]:
    """Canon -> set of lowercase FR/DE alias tokens."""
    out: dict[str, set[str]] = {}
    for canon, langs in types_ref.get("aliases", {}).items():
        toks: set[str] = set()
        for lang in ("fr", "de"):
            for phrase in langs.get(lang, []):
                toks.add(_nfkc_lower(phrase))
        out[canon] = toks
    return out


def text_contains_any_token(text: str, tokens: set[str]) -> bool:
    t = _nfkc_lower(text)
    for tok in tokens:
        if tok and tok in t:
            return True
    return False


def compile_fer_substrings(periodes_ref: dict) -> list[str]:
    subs: list[str] = []
    for pdata in periodes_ref.get("periodes", {}).values():
        for pat in pdata.get("patterns_fr", []) + pdata.get("patterns_de", []):
            subs.append(pat.lower())
    subs.sort(key=len, reverse=True)
    return subs


def text_indicates_fer(datation_1: Any, datation_2: Any, fer_substrings: list[str]) -> bool:
    combined = _nfkc_lower(f"{datation_1 or ''} {datation_2 or ''}")
    if not combined:
        return False
    extra_res = [
        r"\bha\s*[abcd][0-9]?(?:\s*[-/]\s*[bcd][0-9]?)?",
        r"\blt\s*[abcd][0-9]?(?:\s*[-/]\s*[abcd][0-9]?)?",
        r"bze\s*d",
        r"bze\s*c\s*[-/]\s*d",
        r"bze\s*d\s*[-/]\s*ha",
        r"hallstatt",
        r"lat[eè]ne",
        r"charni[eè]re",
        r"transition\s+hallstatt",
        r"ha\s*d3\s*/\s*lt",
        r"âge\s+du\s+fer",
        r"age\s+du\s+fer",
    ]
    for rx in extra_res:
        if re.search(rx, combined, re.IGNORECASE):
            return True
    for sub in fer_substrings:
        if sub and sub in combined:
            return True
    return False


def is_only_bronze_ancien_moyen(datation_1: Any, datation_2: Any) -> bool:
    """True if wording is strictly Bronze ancien/moyen without final / Fer / Ha / LT signals."""
    c = _nfkc_lower(f"{datation_1 or ''} {datation_2 or ''}")
    if not c:
        return False
    if "bronze final" in c or "hallstatt" in c or "latène" in c or "latene" in c:
        return False
    if re.search(r"\bha\s*[abcd]", c) or re.search(r"\blt\s*[abcd]", c):
        return False
    if "âge du fer" in c or "age du fer" in c:
        return False
    if re.search(r"bronze\s+ancien", c) or re.search(r"bronze\s+moyen", c):
        return True
    return False


def has_fer_flag(row: pd.Series) -> bool:
    for c in FER_FLAG_COLS:
        v = row.get(c, 0)
        try:
            if int(float(v)) == 1:
                return True
        except (TypeError, ValueError):
            continue
    return False


def classify_type_site(
    raw: Any,
    structures: Any,
    type_oa: Any,
    type_tokens: dict[str, set[str]],
    report: dict[str, Any],
) -> str:
    r = _nfkc_lower(str(raw)) if raw is not None and not (isinstance(raw, float) and pd.isna(raw)) else ""
    st = str(structures or "")
    oa = _nfkc_lower(str(type_oa or ""))

    def note_unmapped(msg: str) -> None:
        report.setdefault("type_classification_unmapped", []).append(msg)

    if r in ("-", "", "nan"):
        note_unmapped(f"type_site vide ou '-' → INDETERMINE")
        return "INDETERMINE"

    if "habitat" in r and "funéraire" in r:
        if text_contains_any_token(st, type_tokens.get("NECROPOLE", set())):
            return "NECROPOLE"
        return "HABITAT"

    if "funéraire" in r or "funerair" in r:
        tum_toks = type_tokens.get("TUMULUS", set())
        if text_contains_any_token(st, tum_toks):
            return "TUMULUS"
        return "NECROPOLE"

    if r == "habitat":
        op_toks = type_tokens.get("OPPIDUM", set())
        if text_contains_any_token(st, op_toks):
            return "OPPIDUM"
        return "HABITAT"

    if r == "mobilier":
        dep_toks = type_tokens.get("DEPOT", set())
        if text_contains_any_token(st, dep_toks) or "dépôt" in _nfkc_lower(st) or "depot" in _nfkc_lower(st):
            return "DEPOT"
        if "trouvaille" in _nfkc_lower(st) or "isolée" in oa or "isolee" in oa:
            return "DEPOT"
        return "HABITAT"

    if r == "dépôt" or r == "depot":
        return "DEPOT"

    if r == "autre":
        for canon in ("SANCTUAIRE", "ATELIER", "VOIE", "DEPOT", "OPPIDUM", "NECROPOLE", "HABITAT"):
            if text_contains_any_token(st, type_tokens.get(canon, set())):
                return canon
        note_unmapped("autre non résolu par structures → INDETERMINE")
        return "INDETERMINE"

    note_unmapped(f"type_site inconnu: {raw!r}")
    return "INDETERMINE"


def statut_from_type_oa(type_oa: Any) -> str:
    if type_oa is None or (isinstance(type_oa, float) and pd.isna(type_oa)):
        return ""
    t = _nfkc_lower(str(type_oa))
    if "fouille" in t and "diagnostic" not in t:
        return "fouille"
    if "diagnostic" in t:
        return "prospection"
    if "découverte" in t or "decouverte" in t:
        return "signalement"
    return ""


def parse_periode_sous(
    datation_1: Any,
    datation_2: Any,
    periodes_ref: dict,
) -> tuple[str, str, bool]:
    """Returns (periode, sous_periode, parse_ok)."""
    periodes = periodes_ref.get("periodes", {})
    sub_re = re.compile(periodes_ref.get("sub_period_regex", ""), re.IGNORECASE)
    d2 = str(datation_2 or "")
    d1 = str(datation_1 or "")
    combined = f"{d2} {d1}"

    sous = ""
    m = sub_re.search(d2) or sub_re.search(d1)
    if m:
        sous = m.group(0).strip()
        sous = re.sub(r"\s+", " ", sous)

    periode = ""
    cl = combined.lower()
    for pname in ("TRANSITION", "LA_TENE", "HALLSTATT"):
        pdata = periodes.get(pname, {})
        for pat in pdata.get("patterns_fr", []) + pdata.get("patterns_de", []):
            if pat.lower() in cl:
                periode = pname
                break
        if periode:
            break

    if not periode and sous:
        for pname, pdata in periodes.items():
            sdict = pdata.get("sous_periodes") or {}
            for sp_name in sdict:
                sp_compact = sp_name.replace(" ", "")
                so_compact = sous.replace(" ", "")
                if sp_name.lower() in sous.lower() or so_compact.lower() in sp_compact.lower():
                    periode = pname
                    sous = sp_name
                    break
            if periode:
                break

    if not periode:
        if re.search(r"\blt\s*[abcd]", cl, re.I):
            periode = "LA_TENE"
        elif re.search(r"\bha\s*[abcd]", cl, re.I) or "bze" in cl and "ha" in cl:
            periode = "HALLSTATT"

    parse_ok = bool(periode or sous)
    return periode, sous, parse_ok


def read_alsace_sites() -> pd.DataFrame:
    try:
        return pd.read_excel(ALSACE_AF_XLSX, sheet_name="sites", engine="calamine")
    except Exception:
        return pd.read_excel(ALSACE_AF_XLSX, sheet_name="sites", engine="openpyxl")


def build_spatial_lookups(af: pd.DataFrame) -> tuple[dict[tuple[str, str], list[tuple[float, float]]], dict[str, list[tuple[str, float, float]]]]:
    exact: dict[tuple[str, str], list[tuple[float, float]]] = {}
    by_commune: dict[str, list[tuple[str, float, float]]] = {}
    for _, r in af.iterrows():
        c = normalize_place(r.get("commune"))
        ld = normalize_place(r.get("lieu_dit"))
        try:
            lon = float(r["x"])
            lat = float(r["y"])
        except (TypeError, ValueError):
            continue
        if not c:
            continue
        exact.setdefault((c, ld), []).append((lon, lat))
        by_commune.setdefault(c, []).append((ld or "", lon, lat))
    return exact, by_commune


def match_coordinates(
    commune: str,
    lieu_dit: str,
    exact: dict[tuple[str, str], list[tuple[float, float]]],
    by_commune: dict[str, list[tuple[str, float, float]]],
) -> tuple[Optional[float], Optional[float], str]:
    c = normalize_place(commune)
    ld = normalize_place(lieu_dit)
    if not c:
        return None, None, "no_commune"

    pts = exact.get((c, ld))
    if pts:
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
        return lon, lat, "exact_commune_lieu"

    if ld and process is not None:
        candidates = by_commune.get(c)
        if candidates:
            choices = [x[0] for x in candidates]
            hit = process.extractOne(ld, choices, score_cutoff=82)
            if hit:
                _, score, idx = hit
                _, lon, lat = candidates[idx]
                return lon, lat, f"fuzzy_lieu_score_{int(score)}"

    if ld:
        best_lon = best_lat = None
        best_sc = 0
        for lcd, lon, lat in by_commune.get(c, []):
            if not lcd:
                continue
            sc = fuzz.ratio(ld, lcd) if fuzz else 0
            if sc > best_sc:
                best_sc = sc
                best_lon, best_lat = lon, lat
        if best_sc >= 82 and best_lon is not None:
            return best_lon, best_lat, f"fuzzy_lieu_score_{best_sc}"

    return None, None, "no_match"


def to_l93(lon: float, lat: float) -> tuple[float, float]:
    tr = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    x, y = tr.transform(lon, lat)
    return float(x), float(y)


def tokenize_biblio(s: str) -> set[str]:
    parts = re.split(r"[,;]+|\s+et\s+", _nfkc_lower(s))
    return {p.strip() for p in parts if len(p.strip()) > 3}


def load_dedup_targets() -> list[tuple[str, str, str]]:
    """List of (label, key_string, biblio_or_empty); labels uniques par clé pour éviter doublons."""
    seen: set[tuple[str, str]] = set()
    rows: list[tuple[str, str, str]] = []
    if EXISTING_CLEANED.exists():
        ex = pd.read_csv(EXISTING_CLEANED)
        for _, r in ex.iterrows():
            nom = str(r.get("nom_site", "") or "")
            com = str(r.get("commune", "") or "")
            lab = str(r.get("site_id", "")) or nom
            key = f"{normalize_place(com)}|{normalize_place(nom)}"
            sk = (lab, key)
            if sk in seen:
                continue
            seen.add(sk)
            rows.append((lab, key, ""))
    if GOLDEN_CSV.exists():
        g = pd.read_csv(GOLDEN_CSV, sep=";")
        for _, r in g.iterrows():
            com = str(r.get("commune", "") or "")
            raw = str(r.get("raw_text", "") or "")
            lab = f"golden:{com}"
            key = f"{normalize_place(com)}|{normalize_place(raw[:120])}"
            sk = (lab, key)
            if sk in seen:
                continue
            seen.add(sk)
            rows.append((lab, key, ""))
    return rows


def find_duplicates(
    commune: str,
    lieu_dit: str,
    biblio: str,
    targets: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    if not targets or fuzz is None:
        return []
    pk = f"{normalize_place(commune)}|{normalize_place(lieu_dit)}"
    bt = tokenize_biblio(biblio)
    out: list[dict[str, Any]] = []
    seen_lab: set[str] = set()
    for lab, tk, _ in targets:
        sc = fuzz.token_set_ratio(pk, tk)
        if sc < 72:
            continue
        if lab in seen_lab:
            continue
        seen_lab.add(lab)
        reason = f"fuzzy_key={int(sc)}"
        if bt:
            bt2 = tokenize_biblio(tk)
            inter = bt & bt2
            if inter:
                reason += f";biblio_tokens={list(inter)[:5]}"
        out.append({"candidate": lab, "score": int(sc), "reason": reason})
    out.sort(key=lambda x: -x["score"])
    return out[:5]


def main() -> None:
    report: dict[str, Any] = {
        "source": str(PROTO_XLSX.relative_to(ROOT)),
        "fer_filter_policy": (
            "Inclure uniquement si LTAB|LTCD|HaD|BF3_HaC==1 OU texte datation (periodes.json + motifs Ha/LT, "
            "Bze D, Bze C-D, Bze D-Ha, âge du Fer). Exclure le Bronze ancien/moyen pur sans ces signaux. "
            "Sans indicateur Fer : ligne non exportée."
        ),
        "dropped_columns": list(DROP_COLS),
        "patriarche_ea_join": "Non utilisé pour XY : fichier Patriarche sans coordonnées ; EA Proto (float court) incompatible avec Numero_de_l_EA.",
    }

    types_ref = load_json(REF_TYPES)
    periodes_ref = load_json(REF_PERIODES)
    type_tokens = build_flat_type_tokens(types_ref)
    fer_substrings = compile_fer_substrings(periodes_ref)

    df = pd.read_excel(PROTO_XLSX, engine="openpyxl")
    report["row_count_raw"] = len(df)
    report["id_unique_raw"] = int(df["id"].nunique())

    assert len(df) == 1127, f"Attendu 1127 lignes, obtenu {len(df)}"
    assert df.shape[1] == 23, f"Attendu 23 colonnes, obtenu {df.shape[1]}"

    for dc in DROP_COLS:
        if dc in df.columns:
            df = df.drop(columns=[dc])

    for col in STRIP_COLS:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    for col in FLAG_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    def row_included_fer(row: pd.Series) -> bool:
        if has_fer_flag(row):
            return True
        if text_indicates_fer(row.get("datation_1"), row.get("datation_2"), fer_substrings):
            return True
        if is_only_bronze_ancien_moyen(row.get("datation_1"), row.get("datation_2")):
            return False
        # Pas d’indicateur Fer explicite (flags ou texte) : exclu du périmètre exporté
        return False

    df["included_fer_policy"] = df.apply(row_included_fer, axis=1)
    report["row_count_after_fer_filter"] = int(df["included_fer_policy"].sum())

    af = read_alsace_sites()
    exact_map, by_comm_map = build_spatial_lookups(af)

    dedup_targets = load_dedup_targets()
    dup_records: list[dict[str, Any]] = []
    join_success = 0
    period_parse_failures: list[dict[str, str]] = []

    rows_out: list[dict[str, Any]] = []
    report.setdefault("type_classification_unmapped", [])

    for _, row in df.iterrows():
        if not row["included_fer_policy"]:
            continue

        type_canon = classify_type_site(
            row.get("type_site"),
            row.get("structures"),
            row.get("type_oa"),
            type_tokens,
            report,
        )
        periode, sous_per, p_ok = parse_periode_sous(
            row.get("datation_1"),
            row.get("datation_2"),
            periodes_ref,
        )
        if not p_ok:
            d1 = str(row.get("datation_1") or "")
            d2 = str(row.get("datation_2") or "")
            period_parse_failures.append({"datation_1": d1[:120], "datation_2": d2[:120]})

        lon, lat, match_kind = match_coordinates(
            str(row.get("commune") or ""),
            str(row.get("lieu_dit") or ""),
            exact_map,
            by_comm_map,
        )
        x_l93 = y_l93 = ""
        confiance = "LOW"
        if lon is not None and lat is not None:
            join_success += 1
            x_l93, y_l93 = to_l93(lon, lat)
            confiance = "MEDIUM" if match_kind.startswith("exact") else "LOW"

        dups = find_duplicates(
            str(row.get("commune") or ""),
            str(row.get("lieu_dit") or ""),
            str(row.get("biblio") or ""),
            dedup_targets,
        )
        if dups:
            dup_records.append({"id_proto": int(row["id"]), "matches": dups})

        ea_val = row.get("EA")
        ea_out = "" if pd.isna(ea_val) else ea_val

        rows_out.append(
            {
                "site_id": f"PROTO-ALS-{int(row['id'])}",
                "id_proto": int(row["id"]),
                "commune": row.get("commune") if isinstance(row.get("commune"), str) else str(row.get("commune") or ""),
                "lieu_dit": row.get("lieu_dit") if isinstance(row.get("lieu_dit"), str) else str(row.get("lieu_dit") or ""),
                "type_site": row.get("type_site") if not pd.isna(row.get("type_site")) else "",
                "type_site_canon": type_canon,
                "periode": periode,
                "sous_periode": sous_per,
                "datation_1_brut": row.get("datation_1") if not pd.isna(row.get("datation_1")) else "",
                "datation_2_brut": row.get("datation_2") if not pd.isna(row.get("datation_2")) else "",
                "longitude": lon if lon is not None else "",
                "latitude": lat if lat is not None else "",
                "x_l93": x_l93,
                "y_l93": y_l93,
                "statut_fouille": statut_from_type_oa(row.get("type_oa")),
                "confiance": confiance,
                "source": SOURCE_LABEL,
                "bibliographie": row.get("biblio") if isinstance(row.get("biblio"), str) else str(row.get("biblio") or ""),
                "structures_resume": row.get("structures") if isinstance(row.get("structures"), str) else str(row.get("structures") or ""),
                "remarques": row.get("rq") if isinstance(row.get("rq"), str) else str(row.get("rq") or ""),
                "ea": ea_out,
                "oa": row.get("oa") if not pd.isna(row.get("oa")) else "",
            }
        )

    out_df = pd.DataFrame(rows_out)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    report["join_spatial_success_count"] = join_success
    report["duplicates_with_golden_or_sites_csv"] = len(dup_records)
    report["duplicates_detail_sample"] = dup_records[:80]
    report["type_classification_unmapped"] = list(dict.fromkeys(report.get("type_classification_unmapped", [])))
    report["period_parse_failures_count"] = len(period_parse_failures)
    report["period_parse_failures_sample"] = period_parse_failures[:40]
    report["export_row_count"] = len(out_df)
    report["output_csv"] = str(OUT_CSV.relative_to(ROOT))
    report["output_report"] = str(OUT_REPORT.relative_to(ROOT))

    type_dist = out_df["type_site_canon"].value_counts().to_dict()
    periode_dist = out_df["periode"].replace("", "(vide)").value_counts().to_dict()
    report["distribution_type_site_canon"] = {str(k): int(v) for k, v in type_dist.items()}
    report["distribution_periode"] = {str(k): int(v) for k, v in periode_dist.items()}

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({k: report[k] for k in report if k in (
        "row_count_raw", "row_count_after_fer_filter", "export_row_count",
        "join_spatial_success_count", "duplicates_with_golden_or_sites_csv",
        "type_classification_unmapped", "period_parse_failures_count",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
