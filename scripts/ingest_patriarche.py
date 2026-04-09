#!/usr/bin/env python3
"""Ingestion Patriarche — EA âge du Fer (export 20250806) → sites_cleaned + quality_report.

Exécution depuis la racine du dépôt :
  python3 scripts/ingest_patriarche.py
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
PATH_INPUT = ROOT / "data" / "input" / "20250806_Patriarche_ageFer.xlsx"
OUT_DIR = ROOT / "data" / "analysis" / "20250806_Patriarche_ageFer"
PATH_SITES = ROOT / "data" / "output" / "sites.csv"
PATH_GOLDEN = ROOT / "data" / "sources" / "golden_sites.csv"
REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
CACHE_BAN = OUT_DIR / "ban_municipality_cache.json"

SOURCE_TAG = "Patriarche_EA_ageFer_20250806"
EXPECTED_ROWS = 836
BAN_URL = "https://api-adresse.data.gouv.fr/search/"
BAN_DELAY_SEC = 1.0

_DATATION_KEYWORDS = re.compile(
    r"(?i)\b(?:age|âge|hallstatt|fer|bronze|gallo|romain|tène|la\s+tène|"
    r"néolith|mérovingien|médiéval|antiq|moderne|paléolith|mésol|"
    r"indéterminé|eurfer|eurbro)\b"
)
_TYPE_KEYWORDS = re.compile(
    r"(?i)\b(?:habitat|tumulus|nécropole|sépulture|fosse|silo|four|forge|"
    r"tombe|villa|oppidum|fortification|dépôt|enclos|ferme|atelier|"
    r"grenier|fond de cabane|voie|fossé|fanum|sanctuaire|occupation|"
    r"inhumation|crémation|enceinte|épingle|métallique)\b"
)

TYPE_ENUM_FR = {
    "OPPIDUM": "oppidum",
    "HABITAT": "habitat",
    "NECROPOLE": "nécropole",
    "DEPOT": "dépôt",
    "SANCTUAIRE": "sanctuaire",
    "ATELIER": "atelier",
    "VOIE": "voie",
    "TUMULUS": "tumulus",
    "INDETERMINE": "indéterminé",
}

TRANSFORMER_L93_WGS = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
TRANSFORMER_WGS_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


def normalize_text(s: str | float | None) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip()
    if not t or t.lower() == "nan":
        return ""
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    return t


def load_toponyme_map(path: Path) -> dict[str, str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    m: dict[str, str] = {}
    for entry in data.get("concordance", []):
        can = entry.get("canonical", "")
        if not can:
            continue
        m[normalize_text(can)] = can
        for v in entry.get("variants", []):
            m[normalize_text(v)] = can
    return m


def scrub_commune_admin(raw: str | float | None) -> str:
    """Retire les mentions administratives entre parenthèses (ex. « (Périmée !) »)."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()
    return s


# Corrections de saisie fréquentes (clé = normalize_text)
TYPO_COMMUNE: dict[str, str] = {
    "hipsheim": "Hipsheim",
}


def canonical_commune(raw: str | float | None, toponyme_map: dict[str, str]) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    return toponyme_map.get(normalize_text(s), s)


def build_type_alias_map(types_ref: dict) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for canon, langs in types_ref.get("aliases", {}).items():
        for lang in ("fr", "de"):
            for alias in langs.get(lang, []):
                pairs.append((alias.lower(), canon))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def load_period_patterns(periodes_ref: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """Returns (hallstatt_pairs, latene_pairs, transition_pairs) as (lowercase pattern, key)."""
    hall: list[tuple[str, str]] = []
    lat: list[tuple[str, str]] = []
    trans: list[tuple[str, str]] = []
    periodes = periodes_ref["periodes"]
    for p, lang_list in (
        ("HALLSTATT", hall),
        ("LA_TENE", lat),
        ("TRANSITION", trans),
    ):
        block = periodes.get(p, {})
        for pat in block.get("patterns_fr", []):
            lang_list.append((pat.lower(), p))
        for pat in block.get("patterns_de", []):
            lang_list.append((pat.lower(), p))
    for lst in (hall, lat, trans):
        lst.sort(key=lambda x: len(x[0]), reverse=True)
    return hall, lat, trans


def _is_datation(text: str) -> bool:
    return bool(_DATATION_KEYWORDS.search(text))


def _is_type(text: str) -> bool:
    return bool(_TYPE_KEYWORDS.search(text))


def parse_identification(ea_ident: str) -> tuple[list[str], str | None, str | None, str | None, bool]:
    """parts, lieu_dit, chronologie_brute, structure_type_brute, ok."""
    parts = [p.strip() for p in ea_ident.split(" / ")]
    if len(parts) < 3:
        return parts, None, None, None, False

    lieu_dit = parts[4] if len(parts) > 4 and parts[4] else None
    type_mention: str | None = None
    periode_mention: str | None = None
    tail = parts[5:] if len(parts) > 5 else []
    for segment in tail:
        if not segment:
            continue
        if _is_datation(segment) and not periode_mention:
            periode_mention = segment
        elif _is_type(segment) and not type_mention:
            type_mention = segment
        elif not periode_mention and not type_mention:
            if _DATATION_KEYWORDS.search(segment):
                periode_mention = segment
            else:
                type_mention = segment
    ok = bool(parts[2].strip()) and bool(ea_ident.strip())
    return parts, lieu_dit, periode_mention, type_mention, ok


def classify_period(
    chronologie: str | None,
    periodes_ref: dict,
    hall_patterns: list[tuple[str, str]],
    lat_patterns: list[tuple[str, str]],
    trans_patterns: list[tuple[str, str]],
) -> tuple[str, str | None]:
    """Returns (periode label, sous_periode or None)."""
    if not chronologie:
        return "indéterminé", "indéterminé"

    raw_lower = chronologie.lower()
    sub_re = re.compile(periodes_ref.get("sub_period_regex", ""))
    sub_matches = sub_re.findall(chronologie)
    sous = sub_matches[0] if sub_matches else None

    for pat, _ in trans_patterns:
        if pat in raw_lower:
            return "Hallstatt/La Tène", sous or "indéterminé"

    for pat, _ in hall_patterns:
        if pat in raw_lower:
            return "Hallstatt", sous

    for pat, _ in lat_patterns:
        if pat in raw_lower:
            return "La Tène", sous

    if re.search(r"âge\s+du\s+fer|age\s+du\s+fer", raw_lower):
        return "indéterminé", "indéterminé"

    return "indéterminé", sous


def classify_type_token(
    type_raw: str | None,
    sorted_aliases: list[tuple[str, str]],
) -> tuple[str, str | None]:
    """Returns (enum_fr_value, unmapped_token_if_any)."""
    if not type_raw:
        return TYPE_ENUM_FR["INDETERMINE"], None

    tl = type_raw.lower()
    if "épingle" in tl or "objet métallique" in tl or "objet metallique" in tl:
        return TYPE_ENUM_FR["DEPOT"], None
    if "funéraire" in tl or "funeraire" in tl:
        return TYPE_ENUM_FR["NECROPOLE"], None
    if re.search(r"\bvilla\b", tl):
        return TYPE_ENUM_FR["HABITAT"], None
    if "campement" in tl:
        return TYPE_ENUM_FR["HABITAT"], None
    if re.search(r"\benclos\b", tl):
        return TYPE_ENUM_FR["HABITAT"], None

    for alias, canon in sorted_aliases:
        if alias in tl:
            return TYPE_ENUM_FR.get(canon, TYPE_ENUM_FR["INDETERMINE"]), None

    return TYPE_ENUM_FR["INDETERMINE"], type_raw.strip()


def dept_from_numero(numero: str | float | None) -> str | None:
    if numero is None or (isinstance(numero, float) and pd.isna(numero)):
        return None
    m = re.match(r"^\s*(\d{2})\s", str(numero).strip())
    return m.group(1) if m else None


def normalize_ea_num(s: str | float | None) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", "", str(s).strip())


def commune_coord_lookup(
    sites_path: Path,
    golden_path: Path,
    toponyme_map: dict[str, str],
) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]]]:
    """Returns (golden_lonlat_by_norm_commune, sites_l93_stats_by_norm_commune -> mean x,y)."""
    golden_ll: dict[str, tuple[float, float]] = {}
    if golden_path.exists():
        g = pd.read_csv(golden_path, sep=";")
        g["commune_c"] = g["commune"].map(lambda x: canonical_commune(x, toponyme_map))
        for commune, sub in g.groupby("commune_c"):
            if not str(commune).strip():
                continue
            lats = sub["latitude_raw"].dropna().astype(float)
            lons = sub["longitude_raw"].dropna().astype(float)
            if len(lats) and len(lons):
                key = normalize_text(str(commune))
                golden_ll[key] = (float(lons.mean()), float(lats.mean()))

    sites_l93: dict[str, tuple[float, float, float, float]] = {}
    if sites_path.exists():
        s = pd.read_csv(sites_path)
        s = s.dropna(subset=["x_l93", "y_l93"])
        s["commune_c"] = s["commune"].map(lambda x: canonical_commune(x, toponyme_map))
        for commune, sub in s.groupby("commune_c"):
            if not str(commune).strip():
                continue
            key = normalize_text(str(commune))
            sites_l93[key] = (
                float(sub["x_l93"].mean()),
                float(sub["y_l93"].mean()),
            )

    return golden_ll, sites_l93


def l93_to_lonlat(x: float, y: float) -> tuple[float, float]:
    lon, lat = TRANSFORMER_L93_WGS.transform(x, y)
    return lon, lat


def lonlat_to_l93(lon: float, lat: float) -> tuple[float, float]:
    x, y = TRANSFORMER_WGS_L93.transform(lon, lat)
    return x, y


def load_ban_cache() -> dict[str, list[float]]:
    if CACHE_BAN.exists():
        with open(CACHE_BAN, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, list)}
    return {}


def save_ban_cache(cache: dict[str, list[float]]) -> None:
    CACHE_BAN.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_BAN, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0)


def fetch_ban_municipality(commune: str, cache: dict[str, list[float]]) -> tuple[float, float] | None:
    key = normalize_text(commune)
    if key in cache:
        v = cache[key]
        if len(v) < 2:
            return None
        return float(v[0]), float(v[1])
    params = {"q": commune.strip(), "type": "municipality", "limit": 1}
    r = requests.get(BAN_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    feats = data.get("features") or []
    time.sleep(BAN_DELAY_SEC)
    if not feats:
        cache[key] = []
        return None
    geom = feats[0].get("geometry") or {}
    coords = geom.get("coordinates")
    if not coords or len(coords) < 2:
        cache[key] = []
        return None
    lon, lat = float(coords[0]), float(coords[1])
    cache[key] = [lon, lat]
    return lon, lat


def scan_numero_in_dataframes(numero_compact: str, sites_df: pd.DataFrame | None) -> list[dict]:
    if not numero_compact or sites_df is None or sites_df.empty:
        return []
    hits: list[dict] = []
    for idx, row in sites_df.iterrows():
        blob = " ".join(str(v) for v in row.values if pd.notna(v))
        bcompact = normalize_ea_num(blob)
        if numero_compact in bcompact or numero_compact in blob.replace(" ", ""):
            hits.append({"row_index": int(idx), "site_id": row.get("site_id", "")})
            break
    return hits


def main() -> None:
    try:
        import rapidfuzz  # noqa: F401

        fuzzy_available = True
    except ImportError:
        fuzzy_available = False

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(REF_TYPES, encoding="utf-8") as f:
        types_ref = json.load(f)
    with open(REF_PERIODES, encoding="utf-8") as f:
        periodes_ref = json.load(f)

    sorted_aliases = build_type_alias_map(types_ref)
    hall_p, lat_p, trans_p = load_period_patterns(periodes_ref)
    toponyme_map = load_toponyme_map(REF_TOPONYMES)

    df = pd.read_excel(PATH_INPUT, engine="openpyxl")
    if df.shape[0] != EXPECTED_ROWS:
        raise ValueError(f"Attendu {EXPECTED_ROWS} lignes, obtenu {df.shape[0]}")
    expected_cols = [
        "Code_national_de_l_EA",
        "Identification_de_l_EA",
        "Numero_de_l_EA",
        "Nom_de_la_commune",
        "Nom_et_ou_adresse",
    ]
    if list(df.columns) != expected_cols:
        raise ValueError(f"Colonnes inattendues: {list(df.columns)}")

    for col in ("Identification_de_l_EA", "Numero_de_l_EA", "Nom_de_la_commune", "Nom_et_ou_adresse"):
        df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "nan" else x)
        if col != "Nom_et_ou_adresse":
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    def clean_addr(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return pd.NA
        s = str(v).strip()
        if not s or s.lower() == "nan" or s.lower() == "localisation inconnue":
            return pd.NA
        return s

    df["Nom_et_ou_adresse"] = df["Nom_et_ou_adresse"].map(clean_addr)

    golden_ll, sites_l93 = commune_coord_lookup(PATH_SITES, PATH_GOLDEN, toponyme_map)

    sites_full = pd.read_csv(PATH_SITES) if PATH_SITES.exists() else None
    golden_full = pd.read_csv(PATH_GOLDEN, sep=";") if PATH_GOLDEN.exists() else None

    ban_cache = load_ban_cache()
    georef_counts: dict[str, int] = {
        "matched_golden_commune": 0,
        "matched_sites_commune": 0,
        "ban_municipality_centroid": 0,
        "none": 0,
    }
    parsing_failures: list[dict] = []
    unmapped_types: dict[str, int] = {}
    duplicate_hits: list[dict] = []
    fuzzy_pairs: list[dict] = []
    georef_unresolved: list[dict] = []

    rows_out: list[dict] = []

    for _, row in df.iterrows():
        code_nat = int(row["Code_national_de_l_EA"]) if pd.notna(row["Code_national_de_l_EA"]) else row["Code_national_de_l_EA"]
        ea_ident = str(row["Identification_de_l_EA"] or "").strip()
        numero = row["Numero_de_l_EA"]
        numero_s = str(numero).strip() if pd.notna(numero) else ""
        commune_col = scrub_commune_admin(row["Nom_de_la_commune"])
        addr = row["Nom_et_ou_adresse"]

        parts, lieu_dit, chrono_raw, type_raw, parse_ok = parse_identification(ea_ident)
        if not ea_ident or not commune_col:
            parsing_failures.append({"code_national": str(code_nat), "reason": "identification ou commune vide"})
        elif not parse_ok or len(parts) < 5:
            parsing_failures.append({"code_national": str(code_nat), "reason": "segments_insuffisants", "n_parts": len(parts)})

        c_pre = commune_col
        nt_pre = normalize_text(c_pre)
        if nt_pre in TYPO_COMMUNE:
            c_pre = TYPO_COMMUNE[nt_pre]
        commune = canonical_commune(c_pre, toponyme_map)
        commune_key = normalize_text(commune)

        periode, sous_periode = classify_period(chrono_raw, periodes_ref, hall_p, lat_p, trans_p)
        if sous_periode is None:
            sous_periode = ""
        type_site, unmapped_tok = classify_type_token(type_raw, sorted_aliases)
        if unmapped_tok:
            unmapped_types[unmapped_tok] = unmapped_types.get(unmapped_tok, 0) + 1

        lon: float | None = None
        lat: float | None = None
        x_l93: float | None = None
        y_l93: float | None = None
        georef_note = ""
        strategy = "none"

        if commune_key in golden_ll:
            lon, lat = golden_ll[commune_key]
            x_l93, y_l93 = lonlat_to_l93(lon, lat)
            georef_note = "georef=golden_commune_mean;precision=commune"
            strategy = "matched_golden_commune"
            georef_counts[strategy] += 1
        elif commune_key in sites_l93:
            sx, sy = sites_l93[commune_key]
            lon, lat = l93_to_lonlat(sx, sy)
            x_l93, y_l93 = sx, sy
            georef_note = "georef=sites_csv_commune_mean;precision=commune"
            strategy = "matched_sites_commune"
            georef_counts[strategy] += 1
        elif dept_from_numero(numero_s) in ("67", "68"):
            try:
                ll = fetch_ban_municipality(commune, ban_cache)
                if ll:
                    lon, lat = ll
                    x_l93, y_l93 = lonlat_to_l93(lon, lat)
                    georef_note = "georef=ban_municipality;precision=centroïde"
                    strategy = "ban_municipality_centroid"
                    georef_counts[strategy] += 1
                else:
                    georef_note = "ban_no_result"
                    georef_counts["none"] += 1
            except Exception as exc:  # noqa: BLE001
                georef_note = f"ban_error={exc!s}"
                georef_counts["none"] += 1
        else:
            georef_note = "georef=skipped_dept_not_67_68"
            georef_counts["none"] += 1

        confiance = "moyen" if strategy == "ban_municipality_centroid" else "faible"

        if lon is None:
            georef_unresolved.append(
                {
                    "site_id": site_id,
                    "commune": commune,
                    "numero_ea": numero_s,
                    "georef_note": georef_note,
                }
            )

        notes_parts = []
        if lieu_dit:
            notes_parts.append(f"lieu_dit={lieu_dit}")
        if chrono_raw:
            notes_parts.append(f"chrono_brut={chrono_raw}")
        if type_raw:
            notes_parts.append(f"type_brut={type_raw}")
        if georef_note:
            notes_parts.append(georef_note)
        notes_parsing = "; ".join(notes_parts)

        site_id = f"PATRIARCHE-{code_nat}"
        addr_out = "" if pd.isna(addr) else str(addr)

        rows_out.append(
            {
                "site_id": site_id,
                "code_national_ea": code_nat,
                "numero_ea": numero_s,
                "identification_ea_brute": ea_ident,
                "commune": commune,
                "adresse_ou_nom_lieu": addr_out,
                "pays": "FR",
                "longitude": lon if lon is not None else "",
                "latitude": lat if lat is not None else "",
                "x_l93": x_l93 if x_l93 is not None else "",
                "y_l93": y_l93 if y_l93 is not None else "",
                "periode": periode,
                "sous_periode": sous_periode if sous_periode else "",
                "type_site": type_site,
                "confiance": confiance,
                "source": SOURCE_TAG,
                "notes_parsing": notes_parsing,
            }
        )

        ncomp = normalize_ea_num(numero_s)
        if sites_full is not None and ncomp:
            h = scan_numero_in_dataframes(ncomp, sites_full)
            for hit in h:
                duplicate_hits.append(
                    {
                        "patriarche_site_id": site_id,
                        "match": "numero_in_sites_csv_row",
                        "detail": hit,
                    }
                )

        if fuzzy_available and golden_full is not None and lieu_dit:
            from rapidfuzz import fuzz

            best = (0.0, "")
            for _, gr in golden_full.iterrows():
                gcom = canonical_commune(gr["commune"], toponyme_map)
                if normalize_text(gcom) != commune_key:
                    continue
                raw_g = str(gr.get("raw_text", ""))
                score = fuzz.token_set_ratio(lieu_dit.lower(), raw_g.lower()) / 100.0
                if score > best[0]:
                    best = (score, raw_g[:120])
            if best[0] >= 0.85:
                fuzzy_pairs.append({"site_id": site_id, "fuzzy_score": best[0], "golden_excerpt": best[1]})

    save_ban_cache(ban_cache)

    out_df = pd.DataFrame(rows_out)
    out_path = OUT_DIR / "sites_cleaned.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8")

    address_fill_rate = float(df["Nom_et_ou_adresse"].notna().mean())
    report = {
        "row_count_raw": int(len(df)),
        "unique_code_national": int(df["Code_national_de_l_EA"].nunique()),
        "address_fill_rate": round(address_fill_rate, 4),
        "parsing_failures": parsing_failures,
        "georef_strategy_counts": georef_counts,
        "ban_municipality_note": "BAN utilisé pour les départements 67 et 68 (Alsace) lorsque aucune coordonnée n’est trouvée via golden/sites.",
        "georef_unresolved": georef_unresolved,
        "duplicates_with_golden_or_sites_csv": duplicate_hits
        + [{"match": "fuzzy_golden_lieu_dit", **p} for p in fuzzy_pairs],
        "type_classification_unmapped": {
            "counts": unmapped_types,
            "fuzzy_dedup_available": fuzzy_available,
            "fuzzy_dedup_note": None if fuzzy_available else "rapidfuzz non installé — dédup fuzzy commune+lieu-dit non exécutée",
        },
        "type_site_distribution": out_df["type_site"].value_counts().to_dict(),
        "periode_distribution": out_df["periode"].value_counts().to_dict(),
        "georef_rate": round(
            float(sum(1 for x in out_df["longitude"] if x != "" and pd.notna(x))) / max(len(out_df), 1),
            4,
        ),
    }
    with open(OUT_DIR / "quality_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Écrit {out_path} ({len(out_df)} lignes).")
    print(f"Rapport: {OUT_DIR / 'quality_report.json'}")


if __name__ == "__main__":
    main()
