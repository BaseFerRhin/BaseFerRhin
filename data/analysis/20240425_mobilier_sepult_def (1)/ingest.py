#!/usr/bin/env python3
"""
Ingestion mobilier sépultures ODS → sites_cleaned (append), sepultures_mobilier_detail, dedup report.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
from pyproj import Transformer

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILENAME = "20240425_mobilier_sepult_def (1).ods"
MOBILIER_SOURCE_FILE = SOURCE_FILENAME

COL_X = "Coordonnées x (Lambert 93)"
COL_Y = "Coordonnées y (Lambert 93)"
DEDUP_M = 50.0
L93_X_RANGE = (800_000, 1_200_000)
L93_Y_RANGE = (6_100_000, 7_200_000)


def _norm_text(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = unicodedata.normalize("NFKD", str(s).strip().lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _toponym_match(commune: str, lieu_dit: str, ref_commune: str, ref_nom: str) -> bool:
    nc, nl = _norm_text(commune), _norm_text(lieu_dit)
    rc, rn = _norm_text(ref_commune), _norm_text(ref_nom)
    if nc and rc and (nc == rc or nc in rc or rc in nc):
        return True
    if nc and rn and (nc == rn or nc in rn or rn in nc):
        return True
    if nl and rn and (nl in rn or rn in nl or nl == rn):
        return True
    if nl and rc and (nl in rc or nl == rc):
        return True
    return False


def resolve_ods_path() -> Path:
    env = os.environ.get("MOBILIER_ODS_PATH")
    if env and Path(env).is_file():
        return Path(env)
    candidates = [
        REPO_ROOT / "data" / "input" / SOURCE_FILENAME,
        REPO_ROOT / "RawData" / "GrosFichiers - Béhague" / SOURCE_FILENAME,
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "ODS introuvable. Placez le fichier dans data/input/ ou définissez MOBILIER_ODS_PATH. "
        f"Candidats: {[str(c) for c in candidates]}"
    )


def load_subperiod_ranges(periodes: dict) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for _pk, pdata in periodes.get("periodes", {}).items():
        for sp, meta in pdata.get("sous_periodes", {}).items():
            out[sp] = (float(meta["date_debut"]), float(meta["date_fin"]))
    return out


def parse_chrono(
    raw: object,
    sp_ranges: dict[str, tuple[float, float]],
    periodes: dict,
) -> tuple[str, str, float | None, float | None]:
    """Returns (periode, sous_periode, date_debut, date_fin)."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return "indéterminé", "", None, None
    s = str(raw).strip()
    sl = s.lower()

    if "protohistoire" in sl and "indétermin" in sl:
        return "indéterminé", s, None, None

    hallstatt_patterns = periodes["periodes"]["HALLSTATT"]["patterns_fr"] + periodes["periodes"]["HALLSTATT"].get(
        "patterns_de", []
    )
    latene_patterns = periodes["periodes"]["LA_TENE"]["patterns_fr"] + periodes["periodes"]["LA_TENE"].get(
        "patterns_de", []
    )
    transition_patterns = periodes["periodes"]["TRANSITION"]["patterns_fr"] + periodes["periodes"]["TRANSITION"].get(
        "patterns_de", []
    )

    def span_for_keys(keys: list[str]) -> tuple[float | None, float | None]:
        d0, d1 = [], []
        for k in keys:
            if k in sp_ranges:
                a, b = sp_ranges[k]
                d0.append(a)
                d1.append(b)
        if not d0:
            return None, None
        return min(d0), max(d1)

    # Bronze final (hors Ha explicite)
    if re.match(r"^BF\b", s, re.I) and "ha" not in sl:
        return "Bronze final", s, -1200.0, -800.0

    # BF IIIb-Ha C : charnière bronze / Hallstatt
    if re.search(r"bf\s*iii", sl) and "ha" in sl:
        return "Transition", "TRANSITION_BF_HA", -620.0, -500.0

    # Transitions Ha / LT
    if ("lt" in sl or "la tène" in sl) and ("ha" in sl or "hallstatt" in sl):
        a, b = sp_ranges.get("Ha D3 / LT A", (-500.0, -400.0))
        return "Transition", "Ha D3 / LT A" if "?" not in s else s, a, b

    if "ha d3-lt a" in sl or "ha d2-lt a" in sl:
        a, b = sp_ranges.get("Ha D3 / LT A", (-500.0, -400.0))
        return "Transition", s, a, b

    # La Tène — priorité aux motifs LT
    for p in sorted(latene_patterns, key=len, reverse=True):
        if p.lower() in sl or sl == p.lower():
            # extraire LT A, LT B1, etc.
            m = re.search(r"LT\s*[A-D](?:\d)?(?:[a-z])?", s, re.I)
            if m:
                key = m.group(0).replace(" ", "").upper()
                key = re.sub(r"^(LT)([A-D])", r"LT \2", key)
                key = key.replace("LT", "LT ").replace("  ", " ").strip()
                # normaliser "LT A"
                m2 = re.match(r"LT\s*([A-D]\d?[a-z]?)", s, re.I)
                if m2:
                    k = f"LT {m2.group(1).upper()}"
                    if k in sp_ranges:
                        a, b = sp_ranges[k]
                        return "La Tène", k, a, b
            a, b = periodes["periodes"]["LA_TENE"]["date_debut"], periodes["periodes"]["LA_TENE"]["date_fin"]
            return "La Tène", s, float(a), float(b)

    # Hallstatt — plages composées Ha X-Y
    m_range = re.findall(r"Ha\s*([CD]\d?[a-z]?|[D]\d?[a-z]?)", s, re.I)
    if m_range and "lt" not in sl:
        keys = []
        for part in re.split(r"[-/]", s):
            part = part.strip()
            m = re.match(r"Ha\s*([CD]\d?[a-z]?|D\d?[a-z]?)", part, re.I)
            if m:
                label = "Ha " + m.group(1).upper()
                keys.append(label)
        if keys:
            mapped = [k for k in keys if k in sp_ranges]
            if not mapped and any("Ha C" in k for k in keys):
                mapped = ["Ha C"]
            if not mapped:
                for k in keys:
                    kk = re.sub(r"^(Ha [CD]\d).*$", r"\1", k)
                    if kk in sp_ranges:
                        mapped.append(kk)
            if mapped:
                d0, d1 = span_for_keys(mapped)
                return "Hallstatt", s, d0, d1

    # Motifs Hallstatt texte
    for p in sorted(hallstatt_patterns, key=len, reverse=True):
        if len(p) < 3:
            continue
        if p.lower() in sl:
            m = re.search(r"(Ha\s*[CD]\d?|Ha\s*D\d)", s, re.I)
            if m:
                k = re.sub(r"\s+", " ", m.group(0).strip()).title().replace("Ha ", "Ha ")
                k = k.replace("Ha c", "Ha C").replace("Ha d", "Ha D")
                if k in sp_ranges:
                    a, b = sp_ranges[k]
                    return "Hallstatt", k, a, b
            a, b = periodes["periodes"]["HALLSTATT"]["date_debut"], periodes["periodes"]["HALLSTATT"]["date_fin"]
            return "Hallstatt", s, float(a), float(b)

    if sl == "ha" or s == "Ha":
        a, b = periodes["periodes"]["HALLSTATT"]["date_debut"], periodes["periodes"]["HALLSTATT"]["date_fin"]
        return "Hallstatt", s, float(a), float(b)

    # BF seul ou reste
    if sl.startswith("bf") or re.match(r"^bf\b", sl):
        return "Bronze final", s, -1200.0, -800.0

    return "indéterminé", s, None, None


def refine_chrono(row_chrono: str, sp_ranges: dict, periodes: dict) -> tuple[str, str, float | None, float | None]:
    """Second pass with explicit rules for remaining compound strings."""
    base = parse_chrono(row_chrono, sp_ranges, periodes)
    s = str(row_chrono).strip()
    sl = s.lower()

    if base[0] != "indéterminé":
        return base

    # Ha C1, Ha C2, Ha D1a — rattacher Hallstatt
    m = re.match(r"Ha\s*([CD]\d?)[a-z]?", s, re.I)
    if m and "lt" not in sl:
        letter = m.group(1).upper()
        key = f"Ha {letter[0]}{letter[1:] if len(letter) > 1 else ''}"
        if key not in sp_ranges and key.startswith("Ha C"):
            key = "Ha C"
        if key not in sp_ranges and key.startswith("Ha D"):
            key = "Ha D1"
        if key in sp_ranges:
            a, b = sp_ranges[key]
            return "Hallstatt", s, a, b
        a, b = periodes["periodes"]["HALLSTATT"]["date_debut"], periodes["periodes"]["HALLSTATT"]["date_fin"]
        return "Hallstatt", s, float(a), float(b)

    return base


def has_mobilier_val(v: object) -> bool:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) > 0
    t = str(v).strip()
    if not t or t in (".", "—", "-"):
        return False
    if t.lower() in ("x", "?", " ", " "):
        return True
    if re.match(r"^\d", t):
        try:
            return float(t.replace(",", ".")) > 0
        except ValueError:
            return True
    return True


def summarize_armement(g: pd.DataFrame) -> str:
    parts = []
    for label, col in [
        ("épée/poignard", "Fer épée/poignard"),
        ("lance", "Fer lance"),
        ("bouclier", "Fer Bouclier"),
        ("char", "Fer Char"),
    ]:
        if col not in g.columns:
            continue
        n = 0
        for v in g[col]:
            if pd.isna(v):
                continue
            try:
                if float(v) > 0:
                    n += 1
            except (TypeError, ValueError):
                if has_mobilier_val(v) and str(v).strip() not in ("?", "x"):
                    n += 1
        if n:
            parts.append(f"{label}: {n}")
    return " ; ".join(parts) if parts else ""


def summarize_or(g: pd.DataFrame) -> str:
    parts = []
    for col, lab in [("Au Epingle", "Au épingle"), ("Au Anneau", "Au anneau")]:
        if col not in g.columns:
            continue
        tot = 0.0
        for v in g[col]:
            if pd.isna(v):
                continue
            try:
                tot += float(v)
            except (TypeError, ValueError):
                if has_mobilier_val(v):
                    tot += 1
        if tot > 0:
            parts.append(f"{lab}: {tot:g}")
    return " ; ".join(parts) if parts else ""


def mobilier_remarques(g: pd.DataFrame) -> str:
    counts = []
    checks = [
        ("AC Fibule", "fibules"),
        ("AC Torque", "torques"),
        ("AC Bracelet", "bracelets AC"),
        ("Fer Fibule", "fibules fer"),
        ("Vase ossuaire", "vases ossuaires"),
    ]
    for col, name in checks:
        if col not in g.columns:
            continue
        n = sum(1 for v in g[col] if has_mobilier_val(v))
        if n:
            counts.append(f"{name} {n}")
    return "; ".join(counts[:8])


def main() -> None:
    ods_path = resolve_ods_path()
    periodes_path = REPO_ROOT / "data" / "reference" / "periodes.json"
    with open(periodes_path, encoding="utf-8") as f:
        periodes = json.load(f)
    sp_ranges = load_subperiod_ranges(periodes)

    df = pd.read_excel(ods_path, engine="odf", header=0)
    df.columns = (
        df.columns.str.strip()
        .str.replace("Posiiton", "Position", regex=False)
        .str.replace("Offande secondaire", "Offrande secondaire", regex=False)
    )

    # T2: drop empty cols
    df = df.dropna(axis=1, how="all")

    for c in [COL_X, COL_Y]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    bad_xy = df[(df[COL_X] < L93_X_RANGE[0]) | (df[COL_X] > L93_X_RANGE[1]) | (df[COL_Y] < L93_Y_RANGE[0]) | (df[COL_Y] > L93_Y_RANGE[1])]
    xy_warnings = len(bad_xy)

    df["Commune"] = df["Commune"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    df["lieu-dit"] = df["lieu-dit"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    df["N° Sep"] = df["N° Sep"].apply(lambda x: "" if pd.isna(x) else str(x).strip())

    chrono_parsed = df["chrono"].apply(lambda x: refine_chrono(x, sp_ranges, periodes))
    df["periode"] = chrono_parsed.apply(lambda t: t[0])
    df["sous_periode"] = chrono_parsed.apply(lambda t: t[1])
    df["datation_debut"] = chrono_parsed.apply(lambda t: t[2])
    df["datation_fin"] = chrono_parsed.apply(lambda t: t[3])

    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

    def to_wgs(row):
        x, y = row[COL_X], row[COL_Y]
        if pd.isna(x) or pd.isna(y):
            return pd.Series({"longitude": None, "latitude": None})
        lon, lat = transformer.transform(float(x), float(y))
        return pd.Series({"longitude": lon, "latitude": lat})

    wgs = df.apply(to_wgs, axis=1)
    df["longitude"] = wgs["longitude"]
    df["latitude"] = wgs["latitude"]

    cluster_key = df["Commune"] + "|" + df["lieu-dit"]
    df["_cluster"] = cluster_key

    ref_path = REPO_ROOT / "data" / "output" / "sites.csv"
    ref = pd.read_csv(ref_path)
    ref_u = ref.drop_duplicates(subset=["site_id"], keep="first")[
        ["site_id", "nom_site", "commune", "pays", "x_l93", "y_l93"]
    ].copy()
    ref_u["x_l93"] = pd.to_numeric(ref_u["x_l93"], errors="coerce")
    ref_u["y_l93"] = pd.to_numeric(ref_u["y_l93"], errors="coerce")
    ref_fr = ref_u[ref_u["pays"].fillna("").str.upper().isin(["FR", ""])].dropna(subset=["x_l93", "y_l93"])

    dedup_rows = []
    cluster_site_id = {}
    cluster_matched_ref = {}

    for ck, g in df.groupby("_cluster", sort=False):
        xm, ym = float(g[COL_X].mean()), float(g[COL_Y].mean())
        commune = g["Commune"].iloc[0]
        lieu = g["lieu-dit"].iloc[0]
        match_id = None
        best_d = None
        for _, r in ref_fr.iterrows():
            dx = xm - float(r["x_l93"])
            dy = ym - float(r["y_l93"])
            d = (dx * dx + dy * dy) ** 0.5
            if d < DEDUP_M and _toponym_match(commune, lieu, str(r["commune"]), str(r["nom_site"])):
                if best_d is None or d < best_d:
                    best_d = d
                    match_id = r["site_id"]
        h = hashlib.sha256(f"{commune}|{lieu}|{xm:.2f}|{ym:.2f}".encode()).hexdigest()[:16]
        new_id = f"SITE-{h}"
        if match_id:
            cluster_site_id[ck] = match_id
            cluster_matched_ref[ck] = match_id
            dedup_rows.append(
                {
                    "cluster_key": ck,
                    "commune": commune,
                    "lieu_dit": lieu,
                    "x_l93_mean": xm,
                    "y_l93_mean": ym,
                    "match_site_id": match_id,
                    "distance_m": round(best_d, 2) if best_d is not None else "",
                    "status": "matched",
                }
            )
        else:
            cluster_site_id[ck] = new_id
            cluster_matched_ref[ck] = ""
            dedup_rows.append(
                {
                    "cluster_key": ck,
                    "commune": commune,
                    "lieu_dit": lieu,
                    "x_l93_mean": xm,
                    "y_l93_mean": ym,
                    "match_site_id": "",
                    "distance_m": "",
                    "status": "new_site",
                }
            )

    df["site_id"] = df["_cluster"].map(cluster_site_id)

    # Site-level export rows (new only)
    new_site_rows = []
    for ck, g in df.groupby("_cluster", sort=False):
        if cluster_matched_ref[ck]:
            continue
        xm, ym = float(g[COL_X].mean()), float(g[COL_Y].mean())
        commune = g["Commune"].iloc[0]
        lieu = g["lieu-dit"].iloc[0]
        nom_site = f"{commune} — {lieu}" if lieu else commune
        # période dominante (mode)
        per = g["periode"].mode()
        periode = per.iloc[0] if len(per) else "indéterminé"
        sp = g.loc[g["periode"] == periode, "sous_periode"].mode()
        sous = sp.iloc[0] if len(sp) else ""
        dd = g["datation_debut"].median()
        dfm = g["datation_fin"].median()
        lon, lat = transformer.transform(xm, ym)
        sid = cluster_site_id[ck]
        nb = len(g)
        try:
            ref_rel = str(ods_path.resolve().relative_to(REPO_ROOT.resolve()))
        except ValueError:
            ref_rel = MOBILIER_SOURCE_FILE
        new_site_rows.append(
            {
                "site_id": sid,
                "nom_site": nom_site,
                "commune": commune,
                "pays": "FR",
                "type_site": "nécropole",
                "x_l93": xm,
                "y_l93": ym,
                "longitude": lon,
                "latitude": lat,
                "periode": periode,
                "sous_periode": sous,
                "datation_debut": dd if pd.notna(dd) else "",
                "datation_fin": dfm if pd.notna(dfm) else "",
                "source_file": MOBILIER_SOURCE_FILE,
                "armement_summary": summarize_armement(g),
                "or_summary": summarize_or(g),
                "remarques": f"{nb} sépultures. {mobilier_remarques(g)}",
                "phase_id": "",
                "sources_count": nb,
                "source_references": ref_rel,
                "occupation_necropole_raw": "nécropole (sépultures)",
                "chronologie_comment": "",
            }
        )

    cleaned_path = REPO_ROOT / "data" / "output" / "sites_cleaned.csv"
    existing = pd.read_csv(cleaned_path)
    for c in ("source_file", "armement_summary", "or_summary", "remarques"):
        if c not in existing.columns:
            existing[c] = ""
    esc = re.escape(MOBILIER_SOURCE_FILE)
    mask_drop = pd.Series(False, index=existing.index)
    if "source_file" in existing.columns:
        mask_drop |= existing["source_file"].astype(str) == MOBILIER_SOURCE_FILE
    if "source_references" in existing.columns:
        mask_drop |= existing["source_references"].astype(str).str.contains(esc, regex=True, na=False)
    kept = existing[~mask_drop].copy()
    new_df = pd.DataFrame(new_site_rows)
    if new_df.empty:
        out_clean = kept
    else:
        combined_cols = list(dict.fromkeys(list(kept.columns) + [c for c in new_df.columns if c not in kept.columns]))
        for c in combined_cols:
            if c not in kept.columns:
                kept[c] = ""
        for c in combined_cols:
            if c not in new_df.columns:
                new_df[c] = ""
        out_clean = pd.concat([kept[combined_cols], new_df[combined_cols]], ignore_index=True)
    out_clean.to_csv(cleaned_path, index=False)

    # Detail sepultures
    detail_cols = [
        "site_id",
        "Commune",
        "lieu-dit",
        "N° Sep",
        "type sép",
        "chrono",
        "periode",
        "sous_periode",
        "Genre",
        "comptage pondéré/ NMI",
        "Position corps",
        "Décomposition",
        "AC Fibule",
        "AC Bracelet",
        "AC Anneau de jambe",
        "AC Torque",
        "AC Boucle d'oreille",
        "Fer épée/poignard",
        "Fer lance",
        "Fer Char",
        "Roche noire Bracelet",
        "Ambre Perle",
        "Verre Perle",
    ]
    ren = {
        "Commune": "commune",
        "lieu-dit": "lieu_dit",
        "N° Sep": "n_sep",
        "type sép": "type_sep",
        "Genre": "genre",
        "comptage pondéré/ NMI": "nb_ceramique_nmi",
        "Position corps": "position_corps",
        "Décomposition": "decomposition",
    }
    dcols = [c for c in detail_cols if c in df.columns or c == "site_id"]
    detail = df[dcols].rename(columns=ren)
    detail_path = REPO_ROOT / "data" / "output" / "sepultures_mobilier_detail.csv"
    detail.to_csv(detail_path, index=False)

    dedup_df = pd.DataFrame(dedup_rows)
    dedup_path = REPO_ROOT / "data" / "output" / "dedup_mobilier_report.csv"
    dedup_df.to_csv(dedup_path, index=False)

    n_clusters = df["_cluster"].nunique()
    n_matched = sum(1 for v in cluster_matched_ref.values() if v)
    n_new = n_clusters - n_matched
    print("=== Ingestion mobilier sépultures ===")
    print(f"Source ODS: {ods_path}")
    print(f"Lignes sépultures: {len(df)}")
    print(f"Sites agrégés (commune+lieu-dit): {n_clusters}")
    print(f"  — matchés réf. sites.csv (<{DEDUP_M:.0f} m + toponyme): {n_matched}")
    print(f"  — nouveaux ajoutés à sites_cleaned.csv: {n_new}")
    print(f"sepultures_mobilier_detail.csv: {len(detail)} lignes")
    print(f"dedup_mobilier_report.csv: {len(dedup_df)} lignes")
    if xy_warnings:
        print(f"Avertissement: {xy_warnings} lignes hors plages L93 attendues")
    print(f"sites_cleaned.csv total lignes: {len(out_clean)}")


if __name__ == "__main__":
    main()
