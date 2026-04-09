#!/usr/bin/env python3
"""Ingestion ADAB2011 (ArkeoGIS) → sites_cleaned.csv + quality_report.json — BaseFerRhin."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
from pyproj import Transformer
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2].parent
ANALYSIS_DIR = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "data" / "input" / "20250806_ADAB2011_ArkeoGis.csv"
REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
GOLDEN_PATH = ROOT / "data" / "sources" / "golden_sites.csv"
SITES_CLEANED_PATH = ROOT / "data" / "output" / "sites_cleaned.csv"
LOUP_META = ROOT / "data" / "analysis" / "20250806_LoupBernard_ArkeoGis" / "metadata.json"

OUT_SITES = ANALYSIS_DIR / "sites_cleaned.csv"
OUT_REPORT = ANALYSIS_DIR / "quality_report.json"

IRON_START, IRON_END = -800, -25
BBOX_LON = (7.0, 9.0)
BBOX_LAT = (47.5, 49.0)

PERIODE_LABEL = {
    "HALLSTATT": "Hallstatt",
    "LA_TENE": "La Tène",
    "TRANSITION": "Transition",
    "INDETERMINE": "Indéterminé",
}


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = math.radians
    dlon = r(lon2 - lon1)
    dlat = r(lat2 - lat1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(min(1.0, math.sqrt(a)))


def load_toponym_lookup() -> dict[str, str]:
    with open(REF_TOPONYMES, encoding="utf-8") as f:
        data = json.load(f)
    m: dict[str, str] = {}
    for row in data.get("concordance", []):
        can = row["canonical"]
        m[can.strip().lower()] = can
        for v in row.get("variants", []):
            m[str(v).strip().lower()] = can
    return m


def commune_canonical(name: str | float | None, lookup: dict[str, str]) -> str:
    if name is None or (isinstance(name, float) and math.isnan(name)):
        return ""
    s = str(name).strip()
    if not s:
        return ""
    return lookup.get(s.lower(), s)


def as_int_or_none(x: Any) -> int | None:
    if x is None:
        return None
    try:
        if isinstance(x, float) and math.isnan(x):
            return None
    except TypeError:
        pass
    if pd.isna(x):
        return None
    return int(x)


def parse_period_field(raw: str | float | None) -> tuple[int | None, int | None]:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None, None
    s = str(raw).strip()
    if not s or s.lower() in ("indéterminé", "indetermine", "nan"):
        return None, None
    m = re.match(r"^(-?\d+)\s*:\s*(-?\d+)$", s)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def fix_utf8_mojibake(s: str) -> str:
    if not s or ("Ã" not in s and "Â" not in s):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_comment_tags(text: str | float | None) -> dict[str, str]:
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return {}
    s = fix_utf8_mojibake(str(text).replace("\xa0", " "))
    out: dict[str, str] = {}
    for part in s.split("#"):
        part = part.strip()
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        key = key.strip()
        val = val.strip()
        if key in ("DAT_FEIN", "TYP_FEIN", "TYP_GROB", "GENAUIGK_T", "DAT_GROB"):
            out[key] = val
    return out


def parse_precision_m(genau: str | None) -> float | None:
    if not genau:
        return None
    t = genau.lower()
    m = re.search(r"(\d+)\s*m", t)
    if m:
        return float(m.group(1))
    m = re.search(r"bis\s+zu\s+(\d+)\s*m", t)
    if m:
        return float(m.group(1))
    return None


def completeness_score(row: pd.Series) -> int:
    skip = {"", "nan", "indéterminé", "indetermine", "non renseigné", "-1", "non"}
    n = 0
    for c in (
        "SITE_NAME",
        "MAIN_CITY_NAME",
        "LONGITUDE",
        "LATITUDE",
        "STARTING_PERIOD",
        "CARAC_LVL1",
        "CARAC_LVL2",
        "CARAC_LVL3",
        "COMMENTS",
        "BIBLIOGRAPHY",
    ):
        v = row.get(c)
        if pd.isna(v):
            continue
        s = str(v).strip().lower()
        if s and s not in skip:
            n += 1
    if row.get("_d0") is not None and row.get("_d1") is not None:
        n += 2
    tags = row.get("_tags")
    if isinstance(tags, dict) and tags:
        n += len(tags)
    return n


def type_from_typ_fein(text: str | None) -> str | None:
    if not text:
        return None
    t = text.lower()
    if "grabhügel" in t or "hügelgrab" in t:
        return "TUMULUS"
    if "siedlung" in t:
        return "HABITAT"
    if "meiler" in t:
        return "ATELIER"
    if "graben" in t and "wall" not in t:
        return None
    return None


def carac_lvl1_to_type(lvl1: str) -> str:
    m = {
        "Habitat": "HABITAT",
        "Funéraire": "NECROPOLE",
        "Enceinte": "OPPIDUM",
        "Circulation": "VOIE",
        "Structure agraire": "INDETERMINE",
        "Formation superficielle": "INDETERMINE",
        "Charbon": "INDETERMINE",
        "Indéterminé": "INDETERMINE",
        "Céramique": "INDETERMINE",
        "Aménagement hydraulique": "INDETERMINE",
        "Rituel": "SANCTUAIRE",
        "Métal": "INDETERMINE",
        "Autres": "INDETERMINE",
        "Dépôt": "DEPOT",
        "Lithique": "INDETERMINE",
        "Os": "INDETERMINE",
        "Datation": "INDETERMINE",
    }
    return m.get(str(lvl1).strip(), "INDETERMINE")


def build_period_matcher(periodes_ref: dict) -> tuple[dict[str, list[str]], re.Pattern[str]]:
    periodes = periodes_ref["periodes"]
    all_patterns: dict[str, list[str]] = {k: [] for k in periodes}
    for pname, pdata in periodes.items():
        for k in ("patterns_de", "patterns_fr"):
            all_patterns[pname].extend(pdata.get(k, []))
    sub_re = re.compile(periodes_ref.get("sub_period_regex", ""))
    return all_patterns, sub_re


def match_period_from_text(
    text: str,
    all_patterns: dict[str, list[str]],
    sub_re: re.Pattern[str],
    periodes: dict,
) -> tuple[str | None, str | None, int | None, int | None]:
    if not text:
        return None, None, None, None
    tl = text.lower()
    hit: str | None = None
    for pname, pats in all_patterns.items():
        for p in pats:
            if p.lower() in tl:
                hit = pname
                break
        if hit:
            break
    msub = sub_re.search(text) if sub_re.pattern else None
    sous = None
    db = df_end = None
    if msub:
        sub_txt = msub.group(0).replace(" ", "").strip()
        for pname, pdata in periodes.items():
            for sp_name, sp_rng in pdata.get("sous_periodes", {}).items():
                if sp_name.replace(" ", "") == sub_txt.replace(" ", ""):
                    sous = sp_name
                    db, df_end = sp_rng["date_debut"], sp_rng["date_fin"]
                    if not hit:
                        hit = pname
                    break
            if sous:
                break
    return hit, sous, db, df_end


def best_sub_period_for_range(
    lo: int, hi: int, periode_key: str | None, periodes: dict
) -> str | None:
    if not periode_key or periode_key not in periodes:
        return None
    pdata = periodes[periode_key]
    best_sp = None
    best_ov = -1.0
    for sp_name, sp_rng in pdata.get("sous_periodes", {}).items():
        a, b = sp_rng["date_debut"], sp_rng["date_fin"]
        p_lo, p_hi = min(a, b), max(a, b)
        ov = max(0.0, float(min(hi, p_hi) - max(lo, p_lo)))
        if ov > best_ov:
            best_ov = ov
            best_sp = sp_name
    return best_sp if best_ov > 0 else None


def period_from_numeric_range(
    d0: int | None, d1: int | None, periodes: dict
) -> tuple[str | None, str | None, int | None, int | None]:
    if d0 is None or d1 is None:
        return None, None, None, None
    lo, hi = min(d0, d1), max(d0, d1)
    span = hi - lo
    if span > 1200:
        return None, None, d0, d1
    best_p = None
    best_overlap = -1
    for pname, pdata in periodes.items():
        if pname == "TRANSITION":
            continue
        a, b = pdata["date_debut"], pdata["date_fin"]
        p_lo, p_hi = min(a, b), max(a, b)
        ov = max(0, min(hi, p_hi) - max(lo, p_lo))
        if ov > best_overlap:
            best_overlap = ov
            best_p = pname
    if best_overlap <= 0:
        tr = periodes.get("TRANSITION", {})
        a, b = tr.get("date_debut", -500), tr.get("date_fin", -400)
        p_lo, p_hi = min(a, b), max(a, b)
        if max(0, min(hi, p_hi) - max(lo, p_lo)) > 0:
            return "TRANSITION", None, lo, hi
        return None, None, d0, d1
    return best_p, None, d0, d1


def iron_age_overlap(d0: int | None, d1: int | None) -> bool:
    if d0 is None or d1 is None:
        return False
    lo, hi = min(d0, d1), max(d0, d1)
    span = hi - lo
    inter_lo = max(lo, IRON_START)
    inter_hi = min(hi, IRON_END)
    if inter_hi < inter_lo:
        return False
    if span > 1200:
        return False
    return True


def iron_age_from_patterns(text: str, all_patterns: dict[str, list[str]]) -> bool:
    if not text:
        return False
    tl = text.lower()
    for pname in ("HALLSTATT", "LA_TENE", "TRANSITION"):
        for p in all_patterns.get(pname, []):
            pl = p.lower()
            if len(pl) < 4:
                continue
            if pl in tl:
                return True
    if "jüngere eisenzeit" in tl or "ältere eisenzeit" in tl:
        return True
    if "hallstattzeit" in tl or "latènezeit" in tl or "latenezeit" in tl:
        return True
    return False


def confidence_row(centroid_oui: bool, state: str) -> str:
    st = str(state).strip()
    if st == "Prospecté aérien" and not centroid_oui:
        return "MEDIUM"
    return "LOW"


def run() -> None:
    report: dict[str, Any] = {"warnings": [], "mapping_decisions": []}

    with open(REF_TYPES, encoding="utf-8") as f:
        types_ref = json.load(f)
    with open(REF_PERIODES, encoding="utf-8") as f:
        periodes_ref = json.load(f)
    periodes = periodes_ref["periodes"]
    all_patterns, sub_re = build_period_matcher(periodes_ref)
    _ = types_ref

    toponyms = load_toponym_lookup()

    df = pd.read_csv(INPUT_CSV, sep=";", encoding="utf-8")
    report["rows_read"] = len(df)
    if len(df) != 656:
        report["warnings"].append(f"Attendu 656 lignes, lu {len(df)}")

    df["SITE_NAME"] = (
        df["SITE_NAME"]
        .astype(str)
        .str.strip()
        .str.replace(r'"+$', "", regex=True)
        .str.strip()
    )
    df["MAIN_CITY_NAME"] = df["MAIN_CITY_NAME"].astype(str).str.strip()

    d0_list, d1_list = [], []
    for _, r in df.iterrows():
        a, b = parse_period_field(r["STARTING_PERIOD"])
        c, d = parse_period_field(r["ENDING_PERIOD"])
        d0_list.append(a if a is not None else c)
        d1_list.append(b if b is not None else d)
    df["_d0"] = d0_list
    df["_d1"] = d1_list

    tag_rows = [parse_comment_tags(x) for x in df["COMMENTS"]]
    df["_tags"] = tag_rows

    dup_mask = df["SITE_AKG_ID"].duplicated(keep=False)
    dup_ids = df.loc[dup_mask, "SITE_AKG_ID"].unique().tolist()
    report["duplicate_site_akg_ids"] = dup_ids

    df["_score"] = df.apply(completeness_score, axis=1)
    df = df.sort_values("_score", ascending=False).drop_duplicates(subset=["SITE_AKG_ID"], keep="first")
    df = df.drop(columns=["_score"])
    report["unique_sites_after_merge"] = len(df)
    if len(df) != 655:
        report["warnings"].append(f"Attendu 655 sites uniques après agrégation, obtenu {len(df)}")

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)

    rows_out: list[dict[str, Any]] = []
    bbox_exceptions: list[dict[str, Any]] = []
    centroid_oui = 0
    conf_counts: dict[str, int] = {"LOW": 0, "MEDIUM": 0}

    for _, r in df.iterrows():
        sid = int(r["SITE_AKG_ID"])
        lon, lat = float(r["LONGITUDE"]), float(r["LATITUDE"])
        in_bbox = BBOX_LON[0] <= lon <= BBOX_LON[1] and BBOX_LAT[0] <= lat <= BBOX_LAT[1]
        if not in_bbox:
            bbox_exceptions.append(
                {"site_id": f"ADAB2011_{sid}", "lon": lon, "lat": lat, "in_bbox": False}
            )

        x_l93 = y_l93 = None
        try:
            x_l93, y_l93 = transformer.transform(lon, lat)
        except Exception as e:
            report["warnings"].append(f"Projection {sid}: {e}")

        tags = r["_tags"] if isinstance(r["_tags"], dict) else {}
        dat_fein = tags.get("DAT_FEIN", "")
        typ_fein = tags.get("TYP_FEIN", "")
        genau = tags.get("GENAUIGK_T", "")
        precision_m = parse_precision_m(genau)
        com_fixed = fix_utf8_mojibake(str(r["COMMENTS"]))

        base_type = carac_lvl1_to_type(r["CARAC_LVL1"])
        tf = type_from_typ_fein(typ_fein)
        if base_type == "NECROPOLE" and tf == "TUMULUS":
            type_site = "TUMULUS"
        elif tf == "HABITAT":
            type_site = "HABITAT"
        elif tf == "ATELIER":
            type_site = "ATELIER"
        elif tf == "TUMULUS":
            type_site = "TUMULUS"
        else:
            type_site = base_type

        d0, d1 = r["_d0"], r["_d1"]
        d0i = as_int_or_none(d0)
        d1i = as_int_or_none(d1)
        p_txt, sp_txt, db_txt, df_txt = match_period_from_text(
            f"{dat_fein} {com_fixed}", all_patterns, sub_re, periodes
        )
        p_num, sp_num, dbn, dfn = period_from_numeric_range(
            as_int_or_none(d0), as_int_or_none(d1), periodes
        )

        if p_num:
            periode_key = p_num
            sous = sp_num
            dat_debut = float(dbn) if dbn is not None else None
            dat_fin = float(dfn) if dfn is not None else None
            if sp_txt and not sous:
                sous = sp_txt
        elif p_txt:
            periode_key = p_txt
            sous = sp_txt or sp_num
            dat_debut = float(db_txt) if db_txt is not None else (float(dbn) if dbn is not None else None)
            dat_fin = float(df_txt) if df_txt is not None else (float(dfn) if dfn is not None else None)
        else:
            periode_key = None
            sous = sp_txt
            dat_debut = float(d0i) if d0i is not None else None
            dat_fin = float(d1i) if d1i is not None else None

        periode_label = PERIODE_LABEL.get(periode_key or "INDETERMINE", "Indéterminé")
        if not periode_key:
            periode_label = "Indéterminé"

        if periode_key and not sous and d0i is not None and d1i is not None:
            lo, hi = min(d0i, d1i), max(d0i, d1i)
            sp_r = best_sub_period_for_range(lo, hi, periode_key, periodes)
            if sp_r:
                sous = sp_r

        c_oui = str(r["CITY_CENTROID"]).strip().lower() in ("oui", "yes", "true", "1", "y")
        if c_oui:
            centroid_oui += 1
        conf = confidence_row(c_oui, r["STATE_OF_KNOWLEDGE"])
        conf_counts[conf] = conf_counts.get(conf, 0) + 1

        ia_numeric = iron_age_overlap(d0i, d1i)
        ia_class = periode_key in ("HALLSTATT", "LA_TENE", "TRANSITION")
        comment_blob = f"{dat_fein} {com_fixed}"
        ia_text = iron_age_from_patterns(comment_blob, all_patterns)
        tlm = comment_blob.lower()
        metall_ctx = "metallzeit" in tlm or "eisenzeit" in tlm
        wide_iron = False
        if d0i is not None and d1i is not None:
            lo, hi = min(d0i, d1i), max(d0i, d1i)
            wide_iron = (hi - lo) > 1200 and hi >= IRON_START and lo <= IRON_END
        iron_age = ia_numeric or ia_class or ia_text or (wide_iron and metall_ctx)

        bib = str(r["BIBLIOGRAPHY"]).strip() if pd.notna(r["BIBLIOGRAPHY"]) else ""

        rows_out.append(
            {
                "site_id": f"ADAB2011_{sid}",
                "nom_site": r["SITE_NAME"],
                "commune": r["MAIN_CITY_NAME"],
                "pays": "DE",
                "type_site": type_site,
                "longitude": lon,
                "latitude": lat,
                "x_l93": x_l93,
                "y_l93": y_l93,
                "periode": periode_label,
                "sous_periode": sous if sous else "",
                "datation_debut": dat_debut,
                "datation_fin": dat_fin,
                "confiance": conf,
                "precision_m": precision_m if precision_m is not None else "",
                "source": "ADAB2011 / ArkeoGIS",
                "bibliographie": bib,
                "_iron_age": iron_age,
                "_in_bbox": in_bbox,
            }
        )

    out_df = pd.DataFrame(rows_out)
    iron_ids = out_df.loc[out_df["_iron_age"], "site_id"].tolist()
    report["iron_age_sites"] = {"count": len(iron_ids), "site_ids": iron_ids}
    report["bbox"] = {
        "expected": {"lon": list(BBOX_LON), "lat": list(BBOX_LAT)},
        "sites_inside": int(out_df["_in_bbox"].sum()),
        "sites_outside": int((~out_df["_in_bbox"]).sum()),
        "exceptions": bbox_exceptions,
    }
    report["centroids"] = {
        "count_oui": centroid_oui,
        "pct_oui": round(100.0 * centroid_oui / len(out_df), 1) if len(out_df) else 0,
    }
    report["confiance"] = conf_counts

    export_df = out_df.drop(columns=["_iron_age", "_in_bbox"])
    export_df.to_csv(OUT_SITES, index=False, encoding="utf-8")
    report["export_path"] = str(OUT_SITES.relative_to(ROOT))

    golden = pd.read_csv(GOLDEN_PATH, sep=";", encoding="utf-8")
    golden["lat"] = pd.to_numeric(golden["latitude_raw"], errors="coerce")
    golden["lon"] = pd.to_numeric(golden["longitude_raw"], errors="coerce")

    matches_golden: list[dict[str, Any]] = []
    for _, ad in out_df.iterrows():
        alon, alat = ad["longitude"], ad["latitude"]
        acomm = commune_canonical(ad["commune"], toponyms)
        matched_commune = False
        best_fuzz: tuple[float, float, str, str] | None = None
        for _, g in golden.iterrows():
            if pd.isna(g["lat"]) or pd.isna(g["lon"]):
                continue
            d_m = haversine_m(alon, alat, float(g["lon"]), float(g["lat"]))
            gcomm = commune_canonical(g["commune"], toponyms)
            name_sc = float(
                fuzz.ratio(
                    str(ad["nom_site"]).lower(),
                    str(g["raw_text"])[:200].lower(),
                )
            )
            same_c = acomm.lower() == gcomm.lower() or (
                acomm and gcomm and (acomm in gcomm or gcomm in acomm)
            )
            if same_c and d_m < 500:
                matches_golden.append(
                    {
                        "adab_site_id": ad["site_id"],
                        "golden_commune": g["commune"],
                        "distance_m": round(d_m, 1),
                        "decision": "match_commune_500m",
                        "score": None,
                    }
                )
                matched_commune = True
                break
            if name_sc >= 85 and d_m < 5000:
                if best_fuzz is None or d_m < best_fuzz[0]:
                    best_fuzz = (d_m, name_sc, str(g["commune"]), ad["site_id"])
        if not matched_commune and best_fuzz is not None:
            d_m, nsc, gcomm, sid = best_fuzz
            matches_golden.append(
                {
                    "adab_site_id": sid,
                    "golden_commune": gcomm,
                    "distance_m": round(d_m, 1),
                    "decision": "fuzzy_name_geo",
                    "score": round(nsc, 1),
                }
            )

    sc = pd.read_csv(SITES_CLEANED_PATH, encoding="utf-8")
    matches_sc: list[dict[str, Any]] = []
    for _, ad in out_df.iterrows():
        acomm = commune_canonical(ad["commune"], toponyms)
        anom = str(ad["nom_site"]).lower()
        for _, s in sc.iterrows():
            scomm = commune_canonical(s["commune"], toponyms)
            if acomm.lower() != scomm.lower() and acomm and scomm:
                if acomm.lower() not in scomm.lower() and scomm.lower() not in acomm.lower():
                    continue
            snom = str(s["nom_site"]).lower() if pd.notna(s["nom_site"]) else ""
            r_sc = fuzz.token_sort_ratio(anom, snom)
            if r_sc >= 85:
                matches_sc.append(
                    {
                        "adab_site_id": ad["site_id"],
                        "sites_cleaned_id": s["site_id"],
                        "commune_adab": ad["commune"],
                        "commune_sc": s["commune"],
                        "fuzzy": round(r_sc, 1),
                        "decision": "fuzzy_nom_commune",
                    }
                )
                break

    loup_note = "Pas de sites_cleaned pour LoupBernard ; recoupement attendu (Breisach, Offenburg, Freiburg)."
    if LOUP_META.exists():
        with open(LOUP_META, encoding="utf-8") as f:
            lm = json.load(f)
        loup_note += f" Métadonnées : {lm.get('total_rows', '?')} lignes, {lm.get('data_model', {}).get('unique_count', '?')} sites BW âge du Fer."

    report["deduplication"] = {
        "vs_golden_sites": {"match_count": len(matches_golden), "pairs": matches_golden},
        "vs_sites_cleaned": {
            "match_count": len(matches_sc),
            "pairs": matches_sc,
            "note_coords_empty_in_output": True,
        },
        "loup_bernard": loup_note,
    }

    report["summary"] = {
        "lignes_lues": report["rows_read"],
        "sites_exportes": len(export_df),
        "doublons_fusionnes": dup_ids,
    }
    report["classification_summary"] = {
        "type_site": export_df["type_site"].value_counts().to_dict(),
        "periode": export_df["periode"].value_counts().to_dict(),
        "remarques_encodage": "DAT_FEIN / COMMENTS : correction utf-8→latin1→utf-8 si motifs Ã/Â (ex. Latènezeit).",
    }

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Écrit {OUT_SITES} ({len(export_df)} sites)")
    print(f"Écrit {OUT_REPORT}")


if __name__ == "__main__":
    run()
