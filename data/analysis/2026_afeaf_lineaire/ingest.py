#!/usr/bin/env python3
"""Pipeline d'ingestion — 2026_afeaf_lineaire.dbf → sites_cleaned.csv

Source : AFEAF linéaire (27 entités, Alsace, âge du Fer)
Projet : BaseFerRhin
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2].parent
ANALYSIS_DIR = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "data" / "input" / "2026_afeaf_lineaire.dbf"

REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
GOLDEN_SITES = ROOT / "data" / "sources" / "golden_sites.csv"
EXISTING_SITES = ROOT / "data" / "output" / "sites.csv"

COLUMN_MAP = {
    "a": "pays",
    "b": "departement",
    "c": "commune",
    "d": "lieu_dit",
    "e": "categorie_source",
    "f": "chrono_brut",
    "g": "description",
    "h": "detail",
}

SOURCE_ID = "AFEAF_lineaire_2026"


def load_references() -> tuple[dict, dict]:
    with open(REF_TYPES, encoding="utf-8") as f:
        types_ref = json.load(f)
    with open(REF_PERIODES, encoding="utf-8") as f:
        periodes_ref = json.load(f)
    return types_ref, periodes_ref


def fix_mojibake(text: str) -> str:
    """Fix UTF-8 text misread as latin-1."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


# ── T1: Chargement et normalisation ─────────────────────────────────────────

def t1_load_and_normalize(report: dict) -> pd.DataFrame:
    from dbfread import DBF

    table = DBF(str(INPUT_FILE), encoding="latin-1")
    df = pd.DataFrame(iter(table))

    report["t1_encoding_tested"] = "latin-1"
    report["t1_rows_loaded"] = len(df)
    report["t1_columns_raw"] = list(df.columns)

    df = df.rename(columns=COLUMN_MAP)
    report["t1_column_mapping"] = COLUMN_MAP

    text_cols = [c for c in df.columns if df[c].dtype == object]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    for col in text_cols:
        df[col] = df[col].apply(fix_mojibake)

    report["t1_mojibake_fixed"] = True
    report["t1_shp_found"] = False

    shp_candidates = list(INPUT_FILE.parent.glob("2026_afeaf_lineaire.*"))
    shp_exts = [f.suffix for f in shp_candidates]
    report["t1_related_files"] = shp_exts
    if ".shp" in shp_exts:
        report["t1_shp_found"] = True

    return df


# ── T2: Structuration chronologique ─────────────────────────────────────────

def t2_parse_chronology(df: pd.DataFrame, periodes_ref: dict, report: dict) -> pd.DataFrame:
    periodes = periodes_ref["periodes"]
    sub_re = re.compile(periodes_ref.get("sub_period_regex", r"(?:Ha\s*[CD](?:\d)?|LT\s*[A-D](?:\d)?)"))
    c14_re = re.compile(r"c14\s*=\s*(\d+)\s*c[al]*\s*BC\s*-\s*(\d+)\s*cal\s*BC", re.IGNORECASE)
    bf_re = re.compile(r"Bronze\s+(final|moyen|ancien)(?:\s+([I]+(?:[ab])?))?", re.IGNORECASE)
    proto_re = re.compile(r"protohistoire", re.IGNORECASE)

    results = []
    for _, row in df.iterrows():
        raw = row["chrono_brut"]
        chrono_norm = raw
        periode = None
        sous_periode = None
        borne_debut = None
        borne_fin = None

        mc14 = c14_re.search(raw)
        if mc14:
            borne_debut = -int(mc14.group(1))
            borne_fin = -int(mc14.group(2))
            if borne_debut >= periodes["HALLSTATT"]["date_debut"]:
                periode = "HALLSTATT"
            elif borne_debut >= periodes["LA_TENE"]["date_debut"]:
                periode = "LA_TENE"
            else:
                periode = "INDETERMINE"
            results.append((chrono_norm, periode, sous_periode, borne_debut, borne_fin))
            continue

        for pname, pdata in periodes.items():
            for pat in pdata.get("patterns_fr", []):
                if pat.lower() in raw.lower():
                    periode = pname
                    break
            if periode:
                break

        msub = sub_re.search(raw)
        if msub:
            sub_text = msub.group(0).replace(" ", " ").strip()
            for pname, pdata in periodes.items():
                for sp_name, sp_data in pdata.get("sous_periodes", {}).items():
                    if sp_name.replace(" ", "") == sub_text.replace(" ", ""):
                        sous_periode = sp_name
                        borne_debut = sp_data["date_debut"]
                        borne_fin = sp_data["date_fin"]
                        if not periode:
                            periode = pname
                        break
                if sous_periode:
                    break

        if not periode:
            mbf = bf_re.search(raw)
            if mbf:
                periode = "BRONZE_FINAL"
                chrono_norm = raw
            elif proto_re.search(raw):
                periode = "INDETERMINE"

        slash_re = re.compile(r"(Ha\s*D\d?)\s*/\s*(LT\s*[A-D]\d?)", re.IGNORECASE)
        ms = slash_re.search(raw)
        if ms:
            periode = "TRANSITION"
            sous_periode = f"{ms.group(1)}/{ms.group(2)}"
            borne_debut = periodes["TRANSITION"]["date_debut"]
            borne_fin = periodes["TRANSITION"]["date_fin"]

        range_re = re.compile(r"(Ha\s*[CD]\d?)\s*[-/]\s*(D\d)", re.IGNORECASE)
        mr = range_re.search(raw)
        if mr and not sous_periode:
            sous_periode = f"{mr.group(1)}-{mr.group(2)}"

        if not periode:
            age_fer_re = re.compile(r"âge\s+du\s+Fer", re.IGNORECASE)
            age_bz_re = re.compile(r"âge\s+du\s+Bronze", re.IGNORECASE)
            if age_fer_re.search(raw):
                periode = "INDETERMINE_FER"
            elif age_bz_re.search(raw):
                periode = "BRONZE"

        if "LT finale" in raw or "LT Finale" in raw:
            sous_periode = sous_periode or "LT D"
            if not periode:
                periode = "LA_TENE"
            if not borne_debut:
                borne_debut = periodes["LA_TENE"]["sous_periodes"]["LT D1"]["date_debut"]
                borne_fin = periodes["LA_TENE"]["sous_periodes"]["LT D2"]["date_fin"]

        results.append((chrono_norm, periode, sous_periode, borne_debut, borne_fin))

    chrono_df = pd.DataFrame(results, columns=[
        "chrono_texte_normalise", "periode_candidate", "sous_periode_candidate",
        "borne_debut", "borne_fin"
    ])

    for col in chrono_df.columns:
        df[col] = chrono_df[col].values

    period_counts = df["periode_candidate"].value_counts().to_dict()
    report["t2_periode_distribution"] = {str(k): int(v) for k, v in period_counts.items()}
    report["t2_rows_with_dates"] = int(df["borne_debut"].notna().sum())
    report["t2_rows_without_dates"] = int(df["borne_debut"].isna().sum())

    return df


# ── T3: Classification type de site ─────────────────────────────────────────

def t3_classify_type(df: pd.DataFrame, types_ref: dict, report: dict) -> pd.DataFrame:
    aliases = types_ref["aliases"]

    cat_map = {
        "habitat": "HABITAT",
        "indice de site": "INDETERMINE",
    }

    def classify_row(row: pd.Series) -> str:
        cat = row["categorie_source"].lower().strip()
        type_from_cat = cat_map.get(cat)

        text = f"{row['description']} {row['detail']}".lower()
        type_from_text = None
        priority_order = ["OPPIDUM", "NECROPOLE", "SANCTUAIRE", "ATELIER", "VOIE",
                          "TUMULUS", "DEPOT", "HABITAT"]

        for type_code in priority_order:
            for alias in aliases.get(type_code, {}).get("fr", []):
                if alias.lower() in text:
                    type_from_text = type_code
                    break
            if type_from_text:
                break

        if type_from_text and type_from_cat == "INDETERMINE":
            return type_from_text
        if type_from_cat and type_from_cat != "INDETERMINE":
            return type_from_cat
        if type_from_text:
            return type_from_text
        return type_from_cat or "INDETERMINE"

    df["type_site"] = df.apply(classify_row, axis=1)

    type_counts = df["type_site"].value_counts().to_dict()
    report["t3_type_distribution"] = {str(k): int(v) for k, v in type_counts.items()}

    unmapped = df[df["type_site"] == "INDETERMINE"]
    report["t3_indeterminate_count"] = len(unmapped)
    if len(unmapped) > 0:
        report["t3_indeterminate_samples"] = unmapped[["id", "categorie_source", "description"]].head(5).to_dict("records")

    return df


# ── T4: Géoréférencement ────────────────────────────────────────────────────

def t4_georeference(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    df["longitude"] = None
    df["latitude"] = None
    df["x_l93"] = None
    df["y_l93"] = None
    df["spatial_status"] = "no_geometry"

    dept_67 = {"Bas-Rhin"}
    dept_68 = {"Haut-Rhin"}
    valid_depts = dept_67 | dept_68
    invalid_dept = df[~df["departement"].isin(valid_depts)]
    report["t4_spatial_status"] = "no_geometry"
    report["t4_invalid_departments"] = invalid_dept["departement"].unique().tolist() if len(invalid_dept) > 0 else []
    report["t4_dept_distribution"] = df["departement"].value_counts().to_dict()

    return df


# ── T5: Déduplication ───────────────────────────────────────────────────────

def t5_deduplicate(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    matches = []

    if GOLDEN_SITES.exists():
        golden = pd.read_csv(GOLDEN_SITES, sep=";", encoding="utf-8")
        for _, row in df.iterrows():
            commune = row["commune"].lower().strip()
            for _, grow in golden.iterrows():
                gcommune = str(grow["commune"]).lower().strip()
                if commune == gcommune:
                    matches.append({
                        "afeaf_id": int(row["id"]),
                        "afeaf_commune": row["commune"],
                        "afeaf_lieu_dit": row["lieu_dit"],
                        "golden_commune": grow["commune"],
                        "golden_type": grow.get("type_mention", ""),
                        "match_criterion": "commune_exacte",
                    })

    if EXISTING_SITES.exists():
        existing = pd.read_csv(EXISTING_SITES, sep=",", encoding="utf-8")
        for _, row in df.iterrows():
            commune = row["commune"].lower().strip()
            for _, erow in existing.iterrows():
                ecommune = str(erow.get("commune", "")).lower().strip()
                if commune == ecommune:
                    matches.append({
                        "afeaf_id": int(row["id"]),
                        "afeaf_commune": row["commune"],
                        "afeaf_lieu_dit": row["lieu_dit"],
                        "existing_commune": erow.get("commune", ""),
                        "existing_site": erow.get("nom_site", ""),
                        "match_criterion": "commune_sites_csv",
                    })

    unique_matches = []
    seen = set()
    for m in matches:
        key = (m["afeaf_id"], m.get("golden_commune", m.get("existing_commune", "")))
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)

    matched_ids = set(m["afeaf_id"] for m in unique_matches)
    isolates = [int(row["id"]) for _, row in df.iterrows() if row["id"] not in matched_ids]

    report["t5_potential_duplicates"] = unique_matches[:20]
    report["t5_duplicate_count"] = len(unique_matches)
    report["t5_isolate_count"] = len(isolates)
    report["t5_isolate_ids"] = isolates

    return df


# ── T6: Export ──────────────────────────────────────────────────────────────

def t6_export(df: pd.DataFrame, report: dict) -> None:
    export_df = pd.DataFrame({
        "site_id": "AFEAF_LIN_" + df["id"].astype(str),
        "nom_site": df["lieu_dit"],
        "commune": df["commune"],
        "departement": df["departement"],
        "pays": df["pays"],
        "type_site": df["type_site"],
        "longitude": df["longitude"],
        "latitude": df["latitude"],
        "x_l93": df["x_l93"],
        "y_l93": df["y_l93"],
        "periode": df["periode_candidate"],
        "sous_periode": df["sous_periode_candidate"],
        "datation_debut": df["borne_debut"],
        "datation_fin": df["borne_fin"],
        "confiance": "LOW",
        "source": SOURCE_ID,
        "description": df["description"],
        "detail": df["detail"],
        "id_source_afeaf": df["id"],
    })

    out_csv = ANALYSIS_DIR / "sites_cleaned.csv"
    export_df.to_csv(out_csv, index=False, encoding="utf-8")

    report["t6_rows_exported"] = len(export_df)
    report["t6_unique_sites"] = int(export_df["site_id"].nunique())
    report["t6_output_file"] = str(out_csv.relative_to(ROOT))

    report_path = ANALYSIS_DIR / "quality_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    report: dict = {
        "source_file": str(INPUT_FILE.relative_to(ROOT)),
        "export_date_iso": date.today().isoformat(),
        "pipeline": "archeo-ingest / 2026_afeaf_lineaire",
    }

    types_ref, periodes_ref = load_references()

    print("T1 — Chargement et normalisation...")
    df = t1_load_and_normalize(report)
    print(f"  {len(df)} lignes chargées, {len(df.columns)} colonnes")

    print("T2 — Structuration chronologique...")
    df = t2_parse_chronology(df, periodes_ref, report)
    print(f"  Périodes : {report['t2_periode_distribution']}")
    print(f"  Avec dates numériques : {report['t2_rows_with_dates']}/{len(df)}")

    print("T3 — Classification type de site...")
    df = t3_classify_type(df, types_ref, report)
    print(f"  Types : {report['t3_type_distribution']}")

    print("T4 — Géoréférencement...")
    df = t4_georeference(df, report)
    print(f"  Statut spatial : {report['t4_spatial_status']}")

    print("T5 — Déduplication...")
    df = t5_deduplicate(df, report)
    print(f"  Doublons potentiels : {report['t5_duplicate_count']}")
    print(f"  Isolats : {report['t5_isolate_count']}")

    print("T6 — Export...")
    t6_export(df, report)
    print(f"  {report['t6_rows_exported']} lignes exportées → {report['t6_output_file']}")

    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"  Source : {INPUT_FILE.name}")
    print(f"  Lignes source : {report['t1_rows_loaded']}")
    print(f"  Sites exportés : {report['t6_rows_exported']} ({report['t6_unique_sites']} uniques)")
    print(f"  Avec coordonnées : 0% (pas de géométrie .shp disponible)")
    print(f"  Types : {report['t3_type_distribution']}")
    print(f"  Périodes : {report['t2_periode_distribution']}")
    print(f"  Confiance : LOW (pas de coordonnées)")
    print(f"  Doublons potentiels avec existant : {report['t5_duplicate_count']}")
    print(f"  Mojibake corrigé : oui (latin-1 → UTF-8)")
    print(f"  Fichiers : sites_cleaned.csv, quality_report.json")


if __name__ == "__main__":
    main()
