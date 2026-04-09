#!/usr/bin/env python3
"""Pipeline d'ingestion — ea_fr (sample CSV) → sites_cleaned.csv + quality_report.json.

Source : échantillon Entités Archéologiques France (séparateur ;, latin-1).
Projet : BaseFerRhin
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2].parent
ANALYSIS_DIR = Path(__file__).resolve().parent
SAMPLE_CSV = ANALYSIS_DIR / "sample_data.csv"

REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
EXISTING_SITES = ROOT / "data" / "output" / "sites_cleaned.csv"

SOURCE_LABEL = "EA-FR (Entités Archéologiques France)"
BBOX_LON = (7.0, 8.0)
BBOX_LAT = (48.0, 49.0)

# Bornes projet (EUR*) — documentées dans quality_report
EUR_DATATION: dict[str, tuple[float | None, float | None]] = {
    "EURNEO": (-5000.0, -2300.0),
    "EURBRO": (-2300.0, -800.0),
    "EURFER": (-800.0, -25.0),
    "EURGAL": (-25.0, 500.0),
}


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_ea_ident(s: str) -> dict[str, str]:
    """Découpe EA_IDENT sur ' / ' ; détecte permutation période / vestige sur les 2 derniers segments."""
    parts = [p.strip() for p in (s or "").split(" / ")]
    out: dict[str, str] = {
        "ident_num": parts[0] if parts else "",
        "numero_entite": parts[1] if len(parts) > 1 else "",
        "commune_nom": parts[2] if len(parts) > 2 else "",
        "segment_vide_1": parts[3] if len(parts) > 3 else "",
        "lieu": parts[4] if len(parts) > 4 else "",
        "periode_texte": "",
        "vestige_texte": "",
    }
    if len(parts) >= 8:
        out["lieu"] = " / ".join(parts[4:-2])
        out["vestige_texte"] = parts[-2]
        out["periode_texte"] = parts[-1]
        return out

    if len(parts) < 7:
        return out

    a, b = parts[5], parts[6]

    def is_period_text(x: str) -> bool:
        xl = x.lower()
        return bool(
            re.search(r"âge du|age du|gallo|bronze|fer", xl, re.IGNORECASE)
        )

    def is_vestige_text(x: str) -> bool:
        if is_period_text(x):
            return False
        xl = x.lower()
        keys = (
            "silo",
            "fosse",
            "inhumation",
            "habitat",
            "occupation",
            "four",
            "fossé",
            "incinération",
        )
        return any(k in xl for k in keys)

    if is_period_text(a) and not is_period_text(b):
        out["periode_texte"], out["vestige_texte"] = a, b
    elif is_period_text(b) and not is_vestige_text(b) and is_vestige_text(a):
        out["periode_texte"], out["vestige_texte"] = b, a
    else:
        out["periode_texte"], out["vestige_texte"] = a, b
    return out


def eur_key(code: str | float | None) -> str | None:
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return None
    s = str(code).strip().upper()
    if len(s) < 6:
        return None
    return s[:6]


def build_vestige_to_type(types_ref: dict) -> dict[str, str]:
    m: dict[str, str] = {}
    for code, langs in types_ref.get("aliases", {}).items():
        for fr in langs.get("fr", []):
            m[fr.strip().lower()] = code
    m["four"] = "ATELIER"
    return m


def map_vestiges_to_type(vestiges_list: list[str], vmap: dict[str, str]) -> str:
    """Priorité : nécropole > atelier > habitat (reste)."""
    codes: set[str] = set()
    for v in vestiges_list:
        key = (v or "").strip().lower()
        if key in vmap:
            codes.add(vmap[key])
    if "NECROPOLE" in codes:
        return "NECROPOLE"
    if "ATELIER" in codes:
        return "ATELIER"
    if codes:
        return sorted(codes)[0]
    return "INDETERMINE"


def period_from_chrono(
    deb: str | float | None, fin: str | float | None
) -> tuple[str, str, float | None, float | None]:
    """Retourne (periode, sous_periode, datation_debut, datation_fin) projet."""
    d, f = eur_key(deb), eur_key(fin)
    d0, d1 = EUR_DATATION.get(d or "", (None, None)) if d else (None, None)
    f0, f1 = EUR_DATATION.get(f or "", (None, None)) if f else (None, None)

    if d == "EURFER" and f == "EURFER":
        return "Âge du Fer", "Hallstatt – La Tène", -800.0, -25.0
    if d == "EURBRO" and f == "EURFER":
        return "Âge du Bronze – Âge du Fer", "", -2300.0, -25.0
    if d == "EURFER" and f == "EURGAL":
        return "Âge du Fer – Gallo-romain", "", -800.0, 500.0
    if d == "EURBRO" and f == "EURBRO":
        return "Âge du Bronze", "", d0 or -2300.0, d1 or -800.0
    if d == "EURGAL" and f == "EURGAL":
        return "Gallo-romain", "", -25.0, 500.0
    if d == "EURNEO" or f == "EURNEO":
        return "Néolithique / protohistoire", "", d0, f1 or d1

    # Fallback : enveloppe min/max des codes connus
    db = min([x for x in [d0, f0] if x is not None], default=None)
    fn = max([x for x in [d1, f1] if x is not None], default=None)
    labels = []
    if d:
        labels.append(
            {"EURBRO": "Bronze", "EURFER": "Fer", "EURGAL": "Gallo-romain"}.get(
                d, d
            )
        )
    if f and f != d:
        labels.append(
            {"EURBRO": "Bronze", "EURFER": "Fer", "EURGAL": "Gallo-romain"}.get(
                f, f
            )
        )
    periode = " – ".join(labels) if labels else "Indéterminé"
    return periode, "", db, fn


def confidence_from_row(ea_ident: str, deb: Any, fin: Any) -> str:
    if "?" in (ea_ident or ""):
        return "LOW"
    d, f = eur_key(deb), eur_key(fin)
    if d == "EURFER" and f == "EURFER":
        return "HIGH"
    if (d == "EURBRO" and f == "EURFER") or (d == "EURFER" and f == "EURGAL"):
        return "MEDIUM"
    return "MEDIUM"


def format_commune(raw: str) -> str:
    t = raw.strip().replace("_", "-").replace("  ", " ")
    if not t:
        return ""
    parts = [p.capitalize() for p in t.split("-")]
    return "-".join(parts)


def _cell_str(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    return "" if s.lower() == "nan" else s


def t1_load_and_parse(report: dict) -> pd.DataFrame:
    df = pd.read_csv(
        SAMPLE_CSV, sep=";", encoding="latin-1", dtype=str, keep_default_na=False
    )
    # colonnes numériques
    for col in ("NUMORDRE", "NUMERIQUE_", "SURFACE", "ANNEE_DECO", "X_DEGRE", "Y_DEGRE"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    report["t1_source"] = str(SAMPLE_CSV.relative_to(ROOT))
    report["t1_rows_loaded"] = len(df)
    report["t1_note"] = (
        "Échantillon CSV uniquement (pas de DBF complet dans le workspace)."
    )

    mismatches: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        p = parse_ea_ident(str(row.get("EA_IDENT", "")))
        num_csv = str(row.get("NUMERO", "")).strip()
        if p["numero_entite"] and num_csv and p["numero_entite"] != num_csv:
            mismatches.append(
                {
                    "row": int(idx),
                    "ea_natcode": row.get("EA_NATCODE"),
                    "field": "NUMERO",
                    "structured": num_csv,
                    "ea_ident": p["numero_entite"],
                }
            )
        lieu_csv = str(row.get("LIEU_IGN", "")).strip()
        if p["lieu"] and lieu_csv and p["lieu"] != lieu_csv:
            mismatches.append(
                {
                    "row": int(idx),
                    "ea_natcode": row.get("EA_NATCODE"),
                    "field": "LIEU_IGN",
                    "structured": lieu_csv,
                    "ea_ident": p["lieu"],
                }
            )
        ves_csv = str(row.get("VESTIGES", "")).strip().lower()
        ves_p = p["vestige_texte"].strip().lower()
        if ves_p and ves_csv and ves_p != ves_csv:
            mismatches.append(
                {
                    "row": int(idx),
                    "ea_natcode": row.get("EA_NATCODE"),
                    "field": "VESTIGES",
                    "structured": ves_csv,
                    "ea_ident_segment": ves_p,
                }
            )

    report["t1_ea_ident_mismatches"] = mismatches
    report["t1_parser_sample"] = [
        parse_ea_ident(str(x)) for x in df["EA_IDENT"].head(3).tolist()
    ]
    return df


def t2_deduplicate(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Une ligne canonique par EA_NATCODE ; vestiges uniques fusionnés dans la description."""
    multi: dict[str, list[str]] = {}
    for code, g in df.groupby("EA_NATCODE"):
        if len(g) > 1:
            multi[str(code)] = g["VESTIGES"].astype(str).tolist()

    report["t2_multi_line_natcodes"] = multi
    report["t2_merge_count"] = sum(len(v) - 1 for v in multi.values())

    rows_out: list[dict[str, Any]] = []
    for code, g in df.groupby("EA_NATCODE", sort=True):
        g = g.copy()
        # Règle : priorité SURFACE max, puis première ligne ; champs structurés = ligne retenue
        g["_surf"] = pd.to_numeric(g["SURFACE"], errors="coerce").fillna(-1.0)
        g = g.sort_values("_surf", ascending=False)
        base = g.iloc[0]
        vestiges = sorted(
            {str(v).strip() for v in g["VESTIGES"].tolist() if str(v).strip()},
            key=str.lower,
        )
        fusion_note = ""
        if len(vestiges) > 1:
            fusion_note = (
                "Fusion multi-lignes EA_NATCODE ; vestiges distincts : "
                + ", ".join(vestiges)
            )

        rows_out.append(
            {
                **{c: base[c] for c in df.columns if c in base.index},
                "_vestiges_fused": vestiges,
                "_fusion_note": fusion_note,
                "_n_source_rows": len(g),
            }
        )

    out = pd.DataFrame(rows_out)
    report["t2_unique_sites"] = len(out)
    report["t2_fusion_rate_pct"] = round(
        100.0 * report["t2_merge_count"] / max(len(df), 1), 1
    )
    return out


def t3_classify(df: pd.DataFrame, types_ref: dict, report: dict) -> pd.DataFrame:
    vmap = build_vestige_to_type(types_ref)
    report["t3_vestige_alias_map_sample"] = dict(list(vmap.items())[:12])

    types_: list[str] = []
    periodes: list[str] = []
    sous: list[str] = []
    ddeb: list[float | None] = []
    dfin: list[float | None] = []
    conf: list[str] = []

    for _, row in df.iterrows():
        vs = row.get("_vestiges_fused") or [str(row.get("VESTIGES", ""))]
        types_.append(map_vestiges_to_type(list(vs), vmap))
        per, sper, db, fn = period_from_chrono(
            row.get("CHRONO_DEB"), row.get("CHRONO_FIN")
        )
        num = row.get("NUMERIQUE_")
        if num is not None and not (isinstance(num, float) and pd.isna(num)):
            try:
                nv = float(num)
                db = nv if db is None else db
                fn = nv if fn is None else fn
            except (TypeError, ValueError):
                pass
        periodes.append(per)
        sous.append(sper)
        ddeb.append(db)
        dfin.append(fn)
        conf.append(
            confidence_from_row(str(row.get("EA_IDENT", "")), row.get("CHRONO_DEB"), row.get("CHRONO_FIN"))
        )

    df = df.copy()
    df["type_site"] = types_
    df["periode"] = periodes
    df["sous_periode"] = sous
    df["datation_debut"] = ddeb
    df["datation_fin"] = dfin
    df["confiance"] = conf
    return df


def t4_georef(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    lons = pd.to_numeric(df["X_DEGRE"], errors="coerce")
    lats = pd.to_numeric(df["Y_DEGRE"], errors="coerce")
    anomalies: list[dict[str, Any]] = []
    xs: list[float | None] = []
    ys: list[float | None] = []

    for i, (lon, lat, code) in enumerate(
        zip(lons.tolist(), lats.tolist(), df["EA_NATCODE"].tolist())
    ):
        if lon is None or lat is None or pd.isna(lon) or pd.isna(lat):
            xs.append(None)
            ys.append(None)
            anomalies.append(
                {"ea_natcode": code, "reason": "coordonnées manquantes"}
            )
            continue
        if not (BBOX_LON[0] <= lon <= BBOX_LON[1] and BBOX_LAT[0] <= lat <= BBOX_LAT[1]):
            anomalies.append(
                {
                    "ea_natcode": code,
                    "reason": "hors bbox Grand Est / 67 attendue",
                    "lon": lon,
                    "lat": lat,
                }
            )
        x93, y93 = transformer.transform(float(lon), float(lat))
        xs.append(round(x93, 3))
        ys.append(round(y93, 3))

    df = df.copy()
    df["longitude"] = lons
    df["latitude"] = lats
    df["x_l93"] = xs
    df["y_l93"] = ys
    report["t4_bbox"] = {"lon": BBOX_LON, "lat": BBOX_LAT}
    report["t4_anomalies"] = anomalies
    return df


def t5_crossref(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    matches: list[dict[str, Any]] = []
    if not EXISTING_SITES.exists():
        report["t5_existing_sites_path"] = str(EXISTING_SITES)
        report["t5_commune_matches"] = []
        df = df.copy()
        df["_match_existing_site_ids"] = ""
        return df

    ex = pd.read_csv(EXISTING_SITES, encoding="utf-8")
    fr = ex[ex["pays"].astype(str).str.upper() == "FR"].copy()
    fr["_cn"] = fr["commune"].astype(str).str.strip().str.lower()

    toponymes = load_json(REF_TOPONYMES)
    canon_by_variant: dict[str, str] = {}
    for entry in toponymes.get("concordance", []):
        c = entry.get("canonical", "")
        for v in entry.get("variants", []):
            canon_by_variant[str(v).strip().lower()] = c

    def norm_commune(name: str) -> str:
        n = name.strip().lower()
        return canon_by_variant.get(n, name.strip())

    df = df.copy()
    site_ids_col: list[str] = []
    for _, row in df.iterrows():
        raw = parse_ea_ident(str(row.get("EA_IDENT", "")))["commune_nom"]
        commune_fmt = format_commune(raw)
        key = norm_commune(commune_fmt).lower()
        hit = fr[fr["_cn"] == key]
        if len(hit) == 0:
            hit = fr[fr["_cn"] == commune_fmt.lower()]
        if len(hit) > 0:
            ids = ";".join(hit["site_id"].astype(str).head(5).tolist())
            matches.append(
                {
                    "ea_natcode": row["EA_NATCODE"],
                    "commune_ea": commune_fmt,
                    "existing_site_ids_sample": ids,
                    "n_hits": int(len(hit)),
                }
            )
            site_ids_col.append(ids)
        else:
            site_ids_col.append("")

    df["_match_existing_site_ids"] = site_ids_col
    report["t5_commune_matches"] = matches
    report["t5_note"] = (
        "Rattachement par commune normalisée (pas de matching spatial ni EA_NATCODE dans sites_cleaned)."
    )
    return df


def t6_export(df: pd.DataFrame, report: dict) -> None:
    out_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        p = parse_ea_ident(str(row.get("EA_IDENT", "")))
        commune = format_commune(p["commune_nom"])
        dept = ""
        cpp = _cell_str(row.get("COMMUNE_PP"))
        if cpp:
            dept = cpp.split()[0] if cpp.split() else ""

        nom = _cell_str(row.get("NOMUSUEL"))
        if not nom:
            nom = _cell_str(row.get("LIEU_IGN"))
        if not nom:
            nom = commune or _cell_str(row.get("EA_NATCODE"))

        desc_parts = []
        if row.get("_fusion_note"):
            desc_parts.append(str(row["_fusion_note"]))
        if p["periode_texte"]:
            desc_parts.append(f"EA_IDENT période : {p['periode_texte']}")

        out_rows.append(
            {
                "site_id": f"EAFR_{row['EA_NATCODE']}",
                "ea_natcode": str(row["EA_NATCODE"]),
                "nom_site": nom,
                "commune": commune,
                "departement": dept,
                "pays": "FR",
                "type_site": row["type_site"],
                "longitude": row["longitude"],
                "latitude": row["latitude"],
                "x_l93": row["x_l93"],
                "y_l93": row["y_l93"],
                "periode": row["periode"],
                "sous_periode": row["sous_periode"],
                "datation_debut": row["datation_debut"],
                "datation_fin": row["datation_fin"],
                "confiance": row["confiance"],
                "geometrie_ea": str(row.get("GEOMETRIE", "")).strip(),
                "surface": row.get("SURFACE"),
                "source": SOURCE_LABEL,
                "description": " | ".join(desc_parts) if desc_parts else "",
            }
        )

    out_df = pd.DataFrame(out_rows)
    cols = [
        "site_id",
        "ea_natcode",
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
        "geometrie_ea",
        "surface",
        "source",
        "description",
    ]
    out_path = ANALYSIS_DIR / "sites_cleaned.csv"
    out_df[cols].to_csv(out_path, index=False, encoding="utf-8")

    report["t6_output_rows"] = len(out_df)
    report["t6_output_path"] = str(out_path.relative_to(ROOT))

    # Qualité globale
    report["stats"] = {
        "lignes_source": report["t1_rows_loaded"],
        "sites_exportes": len(out_df),
        "taux_fusion_pct": report["t2_fusion_rate_pct"],
        "types_site": out_df["type_site"].value_counts().to_dict(),
        "periodes": out_df["periode"].value_counts().to_dict(),
        "confiance": out_df["confiance"].value_counts().to_dict(),
        "pct_coords_valides": round(
            100.0 * out_df["longitude"].notna().sum() / max(len(out_df), 1), 1
        ),
    }
    report["eur_code_mapping"] = {
        "EURBRO": "Âge du Bronze (bornes projet approx. -2300 / -800)",
        "EURFER": "Âge du Fer Hallstatt–La Tène (-800 / -25)",
        "EURGAL": "Gallo-romain (-25 / 500)",
        "EURNEO": "Néolithique (approx.)",
    }

    qr_path = ANALYSIS_DIR / "quality_report.json"
    with open(qr_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main() -> None:
    report: dict[str, Any] = {
        "generated_for": "ea_fr",
        "pipeline": ["T1", "T2", "T3", "T4", "T5", "T6"],
    }
    types_ref = load_json(REF_TYPES)

    df = t1_load_and_parse(report)
    df = t2_deduplicate(df, report)
    df = t3_classify(df, types_ref, report)
    df = t4_georef(df, report)
    df = t5_crossref(df, report)
    t6_export(df, report)

    print(
        json.dumps(
            {
                "sites_exportes": report["stats"]["sites_exportes"],
                "lignes_source": report["stats"]["lignes_source"],
                "taux_fusion_pct": report["stats"]["taux_fusion_pct"],
                "fichiers": [
                    report["t6_output_path"],
                    "data/analysis/ea_fr/quality_report.json",
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
