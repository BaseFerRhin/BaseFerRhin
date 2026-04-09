#!/usr/bin/env python3
"""Pipeline d'ingestion — 20250806_LoupBernard_ArkeoGis.csv → sites_cleaned.csv + quality_report.json."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyproj import Transformer
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2].parent
ANALYSIS_DIR = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "data" / "input" / "20250806_LoupBernard_ArkeoGis.csv"
REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
GOLDEN_SITES = ROOT / "data" / "sources" / "golden_sites.csv"
EXISTING_SITES = ROOT / "data" / "output" / "sites.csv"

OUTPUT_CSV = ANALYSIS_DIR / "sites_cleaned.csv"
OUTPUT_REPORT = ANALYSIS_DIR / "quality_report.json"

SOURCE_TAG = "ArkeoGIS_LoupBernard_BW_20250806"
PERIOD_RE = re.compile(r"(-?\d+):(-?\d+)")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_period_field(val: str) -> tuple[int, int] | None:
    if pd.isna(val) or not str(val).strip():
        return None
    m = PERIOD_RE.match(str(val).strip())
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return (min(a, b), max(a, b))


def row_date_span(starting: str, ending: str) -> tuple[int, int] | None:
    parts: list[tuple[int, int]] = []
    for field in (starting, ending):
        p = parse_period_field(field)
        if p:
            parts.append(p)
    if not parts:
        return None
    lo = min(lo for lo, _ in parts)
    hi = max(hi for _, hi in parts)
    return lo, hi


def interval_overlap_len(site_lo: int, site_hi: int, p_lo: int, p_hi: int) -> int:
    lo = max(site_lo, p_lo)
    hi = min(site_hi, p_hi)
    if lo > hi:
        return 0
    return hi - lo + 1


def assign_period(
    site_lo: int,
    site_hi: int,
    periodes: dict,
) -> tuple[str, str | None, list[dict]]:
    """Retourne (periode, sous_periode | None, détail scores)."""
    main_names = ("HALLSTATT", "LA_TENE", "TRANSITION")
    scores: dict[str, int] = {}
    details: list[dict] = []
    for name in main_names:
        pdata = periodes[name]
        pl, ph = pdata["date_debut"], pdata["date_fin"]
        ln = interval_overlap_len(site_lo, site_hi, pl, ph)
        scores[name] = ln
        details.append({"periode": name, "overlap_years": ln, "bounds": [pl, ph]})

    max_score = max(scores.values())
    tied = [k for k, v in scores.items() if v == max_score and v > 0]
    if not tied:
        return "HALLSTATT", None, details

    chosen = tied[0]
    if len(tied) > 1 and "TRANSITION" in tied:
        chosen = "TRANSITION"

    sous: str | None = None
    site_len = max(0, site_hi - site_lo + 1)
    pdata = periodes[chosen]
    best_sub = None
    best_sub_len = 0
    for sname, sb in pdata.get("sous_periodes", {}).items():
        sl, sh = sb["date_debut"], sb["date_fin"]
        ol = interval_overlap_len(site_lo, site_hi, sl, sh)
        if ol > best_sub_len:
            best_sub_len = ol
            best_sub = sname
    if site_len > 0 and best_sub and (best_sub_len / site_len) > 0.5:
        sous = best_sub

    return chosen, sous, details


def build_alias_to_canon(types_ref: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for canon, langs in types_ref.get("aliases", {}).items():
        for lang in ("fr", "de"):
            for alias in langs.get(lang, []):
                key = alias.strip().lower()
                out[key] = canon
    return out


def build_toponyme_normalizer(topo_path: Path):
    data = load_json(topo_path)
    variant_to_canonical: dict[str, str] = {}

    def norm(s: str) -> str:
        return str(s).strip().lower()

    for entry in data.get("concordance", []):
        can = entry["canonical"]
        variant_to_canonical[norm(can)] = can
        for v in entry.get("variants", []):
            variant_to_canonical[norm(v)] = can

    def commune_key(s: str) -> str:
        n = norm(s)
        return variant_to_canonical.get(n, n)

    return commune_key


def classify_type_from_lvl1(
    site_akg_id: int,
    unique_lvl1: list[str],
    alias_map: dict[str, str],
    unmapped_log: list[dict],
) -> str:
    if "Enceinte" in unique_lvl1:
        return "OPPIDUM"
    if "Habitat" in unique_lvl1:
        return "HABITAT"
    if "Dépôt" in unique_lvl1:
        return "DEPOT"
    for lvl in unique_lvl1:
        key = lvl.strip().lower()
        if key in alias_map:
            return alias_map[key]
    unmapped_log.append({"SITE_AKG_ID": site_akg_id, "carac_lvl1_values": list(unique_lvl1)})
    return "AUTRE"


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def main() -> None:
    types_ref = load_json(REF_TYPES)
    periodes_ref = load_json(REF_PERIODES)
    periodes = periodes_ref["periodes"]
    alias_map = build_alias_to_canon(types_ref)
    commune_key_fn = build_toponyme_normalizer(REF_TOPONYMES)

    report: dict = {
        "input_file": str(INPUT_CSV.relative_to(ROOT)),
        "export_date_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "row_count_raw": 0,
        "site_count_aggregated": 0,
        "coordinates_out_of_bounds": [],
        "period_inconsistencies": [],
        "type_classification_unmapped": [],
        "duplicates_with_golden_or_sites_csv": [],
        "bibliography_null_count": 0,
        "notes": [
            "100% des points sont des centroïdes communaux (CITY_CENTROID=Oui) — confiance spatiale basse par défaut.",
            "Voir data/analysis/20250806_LoupBernard_ArkeoGis/metadata.json pour le profil source.",
            "Chevauchements attendus avec l’existant : Breisach am Rhein, Heuneburg.",
        ],
    }

    # T1
    df = pd.read_csv(INPUT_CSV, sep=";", encoding="utf-8")
    report["row_count_raw"] = len(df)
    df["SITE_NAME"] = df["SITE_NAME"].astype(str).str.strip()
    df["MAIN_CITY_NAME"] = df["MAIN_CITY_NAME"].astype(str).str.strip()

    # T2 agrégation
    unmapped_types: list[dict] = []
    rows_out: list[dict] = []

    for site_id, g in df.groupby("SITE_AKG_ID", sort=True):
        g = g.reset_index(drop=True)
        caracs: list[dict] = []
        for _, r in g.iterrows():
            caracs.append(
                {
                    "CARAC_NAME": r.get("CARAC_NAME"),
                    "CARAC_LVL1": r.get("CARAC_LVL1"),
                    "CARAC_LVL2": r.get("CARAC_LVL2"),
                    "CARAC_LVL3": r.get("CARAC_LVL3"),
                    "CARAC_LVL4": r.get("CARAC_LVL4"),
                    "CARAC_EXP": r.get("CARAC_EXP"),
                }
            )

        bib_parts: list[str] = []
        for _, r in g.iterrows():
            b = r.get("BIBLIOGRAPHY")
            if pd.notna(b) and str(b).strip():
                bib_parts.append(str(b).strip())
        bib_unique: list[str] = []
        seen_b = set()
        for b in bib_parts:
            if b not in seen_b:
                seen_b.add(b)
                bib_unique.append(b)
        bibliographie = " | ".join(bib_unique)

        comments: list[str] = []
        seen_c = set()
        for _, r in g.iterrows():
            c = r.get("COMMENTS")
            if pd.notna(c) and str(c).strip():
                t = str(c).strip()
                if t not in seen_c:
                    seen_c.add(t)
                    comments.append(t)

        lons = g["LONGITUDE"].dropna().unique().tolist()
        lats = g["LATITUDE"].dropna().unique().tolist()
        cities = g["MAIN_CITY_NAME"].unique().tolist()
        names = g["SITE_NAME"].unique().tolist()

        lon = float(lons[0]) if lons else float("nan")
        lat = float(lats[0]) if lats else float("nan")
        if len(lons) > 1 or len(lats) > 1:
            report.setdefault("intra_group_coordinate_mismatches", []).append(
                {"SITE_AKG_ID": int(site_id), "lons": lons, "lats": lats}
            )
        if len(cities) > 1:
            report.setdefault("intra_group_commune_mismatches", []).append(
                {"SITE_AKG_ID": int(site_id), "cities": cities}
            )
        if len(names) > 1:
            report.setdefault("intra_group_name_mismatches", []).append(
                {"SITE_AKG_ID": int(site_id), "names": names}
            )

        spans: list[tuple[int, int]] = []
        for _, r in g.iterrows():
            sp = row_date_span(str(r["STARTING_PERIOD"]), str(r["ENDING_PERIOD"]))
            if sp:
                spans.append(sp)
        if not spans:
            d_lo, d_hi = 0, 0
            report["period_inconsistencies"].append(
                {"SITE_AKG_ID": int(site_id), "issue": "no_parseable_period"}
            )
        else:
            d_lo = min(lo for lo, _ in spans)
            d_hi = max(hi for _, hi in spans)

        if d_lo > d_hi:
            report["period_inconsistencies"].append(
                {"SITE_AKG_ID": int(site_id), "datation_debut": d_lo, "datation_fin": d_hi}
            )

        unique_lvl1 = []
        seen_l1 = set()
        for _, r in g.iterrows():
            v = r.get("CARAC_LVL1")
            if pd.notna(v) and str(v).strip():
                s = str(v).strip()
                if s not in seen_l1:
                    seen_l1.add(s)
                    unique_lvl1.append(s)

        type_site = classify_type_from_lvl1(int(site_id), unique_lvl1, alias_map, unmapped_types)

        periode, sous_periode, period_details = assign_period(d_lo, d_hi, periodes)
        if all(d["overlap_years"] == 0 for d in period_details):
            report["period_inconsistencies"].append(
                {
                    "SITE_AKG_ID": int(site_id),
                    "issue": "no_overlap_with_HALLSTATT_LA_TENE_TRANSITION",
                    "site_span": [d_lo, d_hi],
                }
            )

        sok = g["STATE_OF_KNOWLEDGE"].iloc[0]
        confiance = "MEDIUM" if str(sok).strip() == "Fouillé" else "LOW"

        rows_out.append(
            {
                "SITE_AKG_ID": int(site_id),
                "nom_site": names[0],
                "commune": cities[0],
                "longitude": lon,
                "latitude": lat,
                "type_site": type_site,
                "periode": periode,
                "sous_periode": sous_periode,
                "datation_debut": d_lo,
                "datation_fin": d_hi,
                "confiance": confiance,
                "bibliographie": bibliographie,
                "caracs": caracs,
            }
        )

    report["type_classification_unmapped"] = unmapped_types
    report["site_count_aggregated"] = len(rows_out)

    # T4 projection
    to_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    to_wgs = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

    for row in rows_out:
        lon, lat = row["longitude"], row["latitude"]
        if not (7.0 <= lon <= 11.0 and 47.0 <= lat <= 50.0):
            report["coordinates_out_of_bounds"].append(
                {
                    "site_id": f"AKG-{row['SITE_AKG_ID']}",
                    "longitude": lon,
                    "latitude": lat,
                }
            )
        try:
            x, y = to_l93.transform(lon, lat)
        except Exception:
            x, y = float("nan"), float("nan")
        row["x_l93"] = x
        row["y_l93"] = y

    # T5 déduplication
    ref_rows: list[dict] = []

    if EXISTING_SITES.exists():
        s_df = pd.read_csv(EXISTING_SITES, sep=",", encoding="utf-8")
        s_df = s_df.drop_duplicates(subset=["site_id"], keep="first")
        for _, r in s_df.iterrows():
            xs, ys = r.get("x_l93"), r.get("y_l93")
            if pd.notna(xs) and pd.notna(ys):
                try:
                    rlon, rlat = to_wgs.transform(float(xs), float(ys))
                except Exception:
                    continue
            else:
                continue
            ref_rows.append(
                {
                    "source": "sites.csv",
                    "site_id": str(r.get("site_id", "")),
                    "nom_site": str(r.get("nom_site", "")),
                    "commune": str(r.get("commune", "")),
                    "pays": str(r.get("pays", "")),
                    "lon": rlon,
                    "lat": rlat,
                }
            )

    if GOLDEN_SITES.exists():
        g_df = pd.read_csv(GOLDEN_SITES, sep=";", encoding="utf-8")
        for _, r in g_df.iterrows():
            try:
                rlat = float(r["latitude_raw"])
                rlon = float(r["longitude_raw"])
            except (KeyError, TypeError, ValueError):
                continue
            ref_rows.append(
                {
                    "source": "golden_sites.csv",
                    "site_id": f"golden:{r.get('commune', '')}",
                    "nom_site": str(r.get("commune", "")),
                    "commune": str(r.get("commune", "")),
                    "pays": "",
                    "lon": rlon,
                    "lat": rlat,
                }
            )

    dup_entries: list[dict] = []
    for row in rows_out:
        sid = f"AKG-{row['SITE_AKG_ID']}"
        our_lon, our_lat = row["longitude"], row["latitude"]
        our_commune_k = commune_key_fn(row["commune"])
        our_nom = row["nom_site"]
        matches: list[dict] = []
        for ref in ref_rows:
            geo_ok = haversine_m(our_lon, our_lat, ref["lon"], ref["lat"]) < 500.0
            ref_ck = commune_key_fn(ref["commune"])
            commune_ok = our_commune_k == ref_ck
            ratio = fuzz.token_sort_ratio(our_nom, ref["nom_site"]) / 100.0
            fuzzy_ok = ratio > 0.85
            if (geo_ok and commune_ok) or fuzzy_ok:
                matches.append(
                    {
                        "ref_source": ref["source"],
                        "ref_site_id": ref["site_id"],
                        "ref_nom": ref["nom_site"],
                        "ref_commune": ref["commune"],
                        "method": "geo+commune" if (geo_ok and commune_ok) else "fuzzy_name",
                        "distance_m": round(haversine_m(our_lon, our_lat, ref["lon"], ref["lat"]), 1),
                        "token_sort_ratio": round(ratio, 3),
                    }
                )
        if matches:
            dup_entries.append({"site_id": sid, "matches": matches})

    report["duplicates_with_golden_or_sites_csv"] = dup_entries

    # T6 export
    export_cols = [
        "site_id",
        "nom_site",
        "commune",
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
        "bibliographie",
    ]
    export_rows = []
    bib_null = 0
    for row in rows_out:
        bib = row["bibliographie"]
        if not bib:
            bib_null += 1
        export_rows.append(
            {
                "site_id": f"AKG-{row['SITE_AKG_ID']}",
                "nom_site": row["nom_site"],
                "commune": row["commune"],
                "pays": "DE",
                "type_site": row["type_site"],
                "longitude": row["longitude"],
                "latitude": row["latitude"],
                "x_l93": row["x_l93"],
                "y_l93": row["y_l93"],
                "periode": row["periode"],
                "sous_periode": row["sous_periode"] if row["sous_periode"] else "",
                "datation_debut": row["datation_debut"],
                "datation_fin": row["datation_fin"],
                "confiance": row["confiance"],
                "source": SOURCE_TAG,
                "bibliographie": bib,
            }
        )
    report["bibliography_null_count"] = bib_null

    out_df = pd.DataFrame(export_rows, columns=export_cols)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUTPUT_CSV} ({len(out_df)} rows)")
    print(f"Wrote {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
