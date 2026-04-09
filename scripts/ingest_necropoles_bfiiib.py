#!/usr/bin/env python3
"""
Ingestion Excel « nécropoles BF IIIb – Ha D3 Alsace-Lorraine » (BaseFerRhin).
Pipeline T1–T6 : chargement, nettoyage, classification multi-phases, projection L93→WGS84,
déduplication vs data/output/sites.csv, export sites_cleaned.csv + ingest_report.csv.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from pathlib import Path

import pandas as pd
from pyproj import Transformer

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_NAME = "20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx"
SOURCE_CANDIDATES = [
    REPO_ROOT / "data/input" / SOURCE_NAME,
    REPO_ROOT / "RawData/GrosFichiers - Béhague" / SOURCE_NAME,
]

REF_PERIODES = REPO_ROOT / "data/reference/periodes.json"
REF_TOPONYMES = REPO_ROOT / "data/reference/toponymes_fr_de.json"
SITES_CSV = REPO_ROOT / "data/output/sites.csv"
OUT_CLEANED = REPO_ROOT / "data/output/sites_cleaned.csv"
OUT_REPORT = REPO_ROOT / "data/output/ingest_report.csv"
BACKUP_SUFFIX = "sites_cleaned_pre_necropoles_bfiiib.csv"

# Déduplication T5 : fenêtre métrique (m) entre le min et max demandés
MATCH_DIST_MIN_M = 30.0
MATCH_DIST_MAX_M = 80.0
MATCH_DIST_USED_M = 55.0

SOURCE_REF_REL = f"data/input/{SOURCE_NAME}"
INGEST_TAG = "necropoles-bfiiib-ha-d3"

# Colonnes Excel → phase (sous_période affichée, bornes BC depuis l’intitulé ou référentiel)
PHASE_COLUMN_SPECS: list[tuple[str, str, str, int | None, int | None]] = [
    ("Hallstatt B2-B3 (850-800)", "Hallstatt", "Ha B2-B3", -850, -800),
    ("Hallstatt C1 (800-660)", "Hallstatt", "Ha C", -800, -660),
    ("Hallstatt C2 (660-620)", "Hallstatt", "Ha C", -660, -620),
    ("Hallstatt D1 (620-550)", "Hallstatt", "Ha D1", -620, -550),
    ("Hallstatt D2 (550-500)", "Hallstatt", "Ha D2", -550, -500),
    ("Hallstatt D3 (500-480)", "Hallstatt", "Ha D3", -500, -480),
]

TERTRE_COLS = ["Tertre (élévation)", "Tertre arasé"]


def resolve_source_path() -> Path:
    for p in SOURCE_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Fichier source introuvable. Cherché:\n  " + "\n  ".join(str(p) for p in SOURCE_CANDIDATES)
    )


def ascii_fold(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip()
    if not t:
        return ""
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.lower()


def collapse_spaces(s: str) -> str:
    if not isinstance(s, str):
        return s
    return re.sub(r"\s+", " ", s.strip())


def load_toponyme_maps(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, str] = {}
    for row in data.get("concordance", []):
        can = row.get("canonical") or ""
        if not can:
            continue
        for v in [can] + (row.get("variants") or []):
            k = ascii_fold(v)
            if k and k not in out:
                out[k] = can
    return out


def normalize_commune(name: str, variant_map: dict[str, str]) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = collapse_spaces(str(name))
    if not s:
        return ""
    k = ascii_fold(s)
    if k in variant_map:
        return variant_map[k]
    k2 = ascii_fold(s.replace("-", " "))
    return variant_map.get(k2, s)


def load_periode_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_datation_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t.strip())
    t = re.sub(r"La\s*Tène", "La Tène", t, flags=re.I)
    t = re.sub(r"\bLTA\b", "LT A", t, flags=re.I)
    t = re.sub(r"\bLTB\b", "LT B", t, flags=re.I)
    t = re.sub(r"\bLTC\b", "LT C", t, flags=re.I)
    t = re.sub(r"\bLTD\b", "LT D", t, flags=re.I)
    t = re.sub(r"LT\s*A(\d)", r"LT A\1", t, flags=re.I)
    return t


def parse_periode_from_text(
    datation: object,
    occupation: object,
    periodes_cfg: dict,
) -> tuple[str, str | None, int | None, int | None, str]:
    """
    Retourne (periode, sous_periode, datation_debut, datation_fin, commentaire_parse).
    """
    periodes = periodes_cfg.get("periodes", {})
    sub_re = periodes_cfg.get("sub_period_regex", "")

    def pick_text() -> str:
        for col in (datation, occupation):
            if col is None or (isinstance(col, float) and pd.isna(col)):
                continue
            s = collapse_spaces(str(col))
            if s and s not in ("-", "?"):
                return s
        return ""

    raw_combined = pick_text()
    if not raw_combined:
        return "indéterminé", None, None, None, ""

    text = normalize_datation_text(raw_combined)
    tl = text.lower()

    if re.search(r"\bbz\b|bronze\s*moyen|bronze\s*final|\bbm\b", tl) and not re.search(
        r"hallstatt|ha\s*[cd]|la\s*tène|latène|lt\s*[a-d]", tl
    ):
        return "Bronze final", None, None, None, "Bz détecté sans Fer explicite"

    hall_cfg = periodes.get("HALLSTATT", {})
    lt_cfg = periodes.get("LA_TENE", {})
    trans_cfg = periodes.get("TRANSITION", {})

    def match_patterns(cfg: dict, blob: str) -> bool:
        for p in cfg.get("patterns_fr", []) + cfg.get("patterns_de", []):
            if p and re.search(re.escape(p), blob, re.I):
                return True
        return False

    is_ha = match_patterns(hall_cfg, text) or bool(re.search(r"\bha\s*[cd]\d?", tl))
    is_lt = match_patterns(lt_cfg, text) or bool(re.search(r"\blt\s*[a-d]\d?", tl))
    is_trans = match_patterns(trans_cfg, text) or bool(
        re.search(r"ha\s*d3\s*[-/]\s*lt\s*a|d3\s*[-–]\s*lt\s*a|hallstatt.*lt\s*a", tl)
    )

    sous: str | None = None
    if sub_re:
        m = re.findall(sub_re, text, flags=re.I)
        if m:
            sous = m[-1].replace("  ", " ")
            sous = re.sub(r"\s+", " ", sous.strip())
            if re.match(r"^ha\s", sous, re.I):
                sous = re.sub(r"^ha\s*", "Ha ", sous, flags=re.I)
            if re.match(r"^lt\s", sous, re.I):
                sous = re.sub(r"^lt\s*", "LT ", sous, flags=re.I)

    if is_trans or (is_ha and is_lt and re.search(r"lt\s*a|d3", tl)):
        sp = trans_cfg.get("sous_periodes", {}).get("Ha D3 / LT A", {})
        return (
            "Hallstatt",
            "Ha D3 / LT A",
            sp.get("date_debut"),
            sp.get("date_fin"),
            "Transition / texte mixte",
        )

    if is_lt and not is_ha:
        periode = "La Tène"
        lt_subs = lt_cfg.get("sous_periodes", {})
        if sous:
            sk = sous.replace(" ", "").upper()
            for k in lt_subs:
                if sk.replace(" ", "").upper() in k.replace(" ", "").upper() or k.upper() in sous.upper():
                    sp = lt_subs[k]
                    return periode, k, sp.get("date_debut"), sp.get("date_fin"), ""
        return periode, sous, lt_cfg.get("date_debut"), lt_cfg.get("date_fin"), ""

    if is_ha:
        periode = "Hallstatt"
        ha_subs = hall_cfg.get("sous_periodes", {})
        if not sous:
            mh = re.search(r"Hallstatt\s+([CD])(\d?)\b", text, re.I)
            if mh:
                g1, g2 = mh.group(1).upper(), mh.group(2)
                sous = f"Ha {g1}" + (g2 if g2 else "")
        if sous:
            for k in ha_subs:
                if k.replace(" ", "").lower() in sous.replace(" ", "").lower():
                    sp = ha_subs[k]
                    return periode, k, sp.get("date_debut"), sp.get("date_fin"), ""
        return periode, sous, hall_cfg.get("date_debut"), hall_cfg.get("date_fin"), ""

    if re.search(r"hallstatt", tl):
        return "Hallstatt", sous, hall_cfg.get("date_debut"), hall_cfg.get("date_fin"), ""

    if re.search(r"\bbz\b|protohistoire", tl):
        return "indéterminé", sous, None, None, "Bz/Protohistoire sans résolution Fer"

    return "indéterminé", sous, None, None, ""


def apply_sous_periode_dates(
    periode: str, sous: str | None, periodes_cfg: dict
) -> tuple[int | None, int | None]:
    if not sous:
        return None, None
    periodes = periodes_cfg.get("periodes", {})
    if periode == "Hallstatt":
        subs = periodes.get("HALLSTATT", {}).get("sous_periodes", {})
        for k, sp in subs.items():
            if k.replace(" ", "").lower() in sous.replace(" ", "").lower():
                return sp.get("date_debut"), sp.get("date_fin")
    if periode == "La Tène":
        subs = periodes.get("LA_TENE", {}).get("sous_periodes", {})
        for k, sp in subs.items():
            if k.replace(" ", "").lower() in sous.replace(" ", "").lower():
                return sp.get("date_debut"), sp.get("date_fin")
    if periode == "Hallstatt" and sous == "Ha D3 / LT A":
        sp = periodes.get("TRANSITION", {}).get("sous_periodes", {}).get("Ha D3 / LT A", {})
        return sp.get("date_debut"), sp.get("date_fin")
    return None, None


def is_phase_column_active(val: object) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip().lower()
    if s in ("", "-", "0", "nan", "non", "à vérifier", "a verifier"):
        return False
    if s in ("1", "oui", "o", "yes", "x"):
        return True
    try:
        return float(s) == 1.0
    except ValueError:
        return False


def is_tertre_signal(val: object) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip().lower()
    if s in ("", "-", "0", "nan"):
        return False
    if s in ("1", "oui", "o", "yes", "x", "plusieurs"):
        return True
    try:
        return float(s) > 0
    except ValueError:
        return True


def coord_outlier_xy(x: float | None, y: float | None) -> bool:
    if x is None or y is None:
        return True
    if y < 6_000_000:
        return True
    # Emprise élargie Alsace-Lorraine + Bade voisine (L93)
    if not (800_000 <= x <= 1_250_000 and 6_000_000 <= y <= 6_960_000):
        return True
    return False


def new_site_id(commune: str, nom: str, x: float | None, y: float | None, row_index: int) -> str:
    key = f"{commune}|{nom}|{x}|{y}|{row_index}|{INGEST_TAG}"
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f"SITE-{h}"


def new_phase_id(site_id: str, sous: str | None, dd: int | None, df: int | None, row_index: int, pidx: int) -> str:
    key = f"{site_id}|{sous}|{dd}|{df}|{row_index}|{pidx}|{INGEST_TAG}"
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f"SITE-{h}-PH1"


def commune_similar(a: str, b: str) -> bool:
    fa, fb = ascii_fold(a), ascii_fold(b)
    if not fa or not fb:
        return False
    return fa == fb or fa in fb or fb in fa


def dist_m(x1: float, y1: float, x2: float, y2: float) -> float:
    return float(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)


def main() -> None:
    src_path = resolve_source_path()
    periodes_cfg = load_periode_config(REF_PERIODES)
    variant_map = load_toponyme_maps(REF_TOPONYMES)

    # T1
    df = pd.read_excel(src_path, engine="openpyxl", header=0)
    df.columns = df.columns.str.strip()
    if "Unnamed: 0" in df.columns:
        df = df.rename(columns={"Unnamed: 0": "row_index"})
    df = df.dropna(how="all")

    anomalies: dict[str, int] = {
        "non_localise_nom": 0,
        "coord_bad": 0,
        "coord_missing": 0,
        "phase_a_verifier": 0,
    }

    # T2 — Dept str
    df["Dept"] = df["Dept"].apply(
        lambda v: ""
        if v is None or (isinstance(v, float) and pd.isna(v))
        else str(int(v)) if str(v).replace(".0", "").isdigit() else str(v).strip()
    )

    df["Commune"] = df["Commune"].apply(
        lambda x: collapse_spaces(str(x)) if pd.notna(x) and str(x).strip() else ""
    )
    df["commune_norm"] = df["Commune"].apply(lambda c: normalize_commune(c, variant_map))

    # Nom / non localisé
    def norm_nom(row: pd.Series) -> str:
        nonlocal_nl = {"non localisé", "non localise", "non-localisé"}
        raw = row.get("Nom")
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return ""
        s = collapse_spaces(str(raw))
        if ascii_fold(s) in {ascii_fold(x) for x in nonlocal_nl}:
            anomalies["non_localise_nom"] += 1
            com = row.get("commune_norm") or row.get("Commune") or ""
            com = str(com).strip()
            return f"{com} (nécropole non localisée)" if com else "nécropole non localisée"
        return s

    df["nom_site"] = df.apply(norm_nom, axis=1)

    def fill_empty_nom(r: pd.Series) -> str:
        n = str(r.get("nom_site") or "").strip()
        if n:
            return n
        com = str(r.get("commune_norm") or r.get("Commune") or "").strip()
        return f"{com} (nécropole)" if com else "nécropole sans nom"

    df["nom_site"] = df.apply(fill_empty_nom, axis=1)

    xcol, ycol = "Coordonnées x (Lambert 93)", "Coordonnées y (Lambert 93)"

    def parse_coord(v: object) -> float | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    df["x_l93"] = df[xcol].apply(parse_coord)
    df["y_l93"] = df[ycol].apply(parse_coord)

    df["coord_quality"] = "ok"
    for i in df.index:
        x, y = df.at[i, "x_l93"], df.at[i, "y_l93"]
        if x is None or y is None:
            df.at[i, "coord_quality"] = "bad"
            anomalies["coord_missing"] += 1
        elif coord_outlier_xy(x, y):
            df.at[i, "coord_quality"] = "bad"
            anomalies["coord_bad"] += 1

    # Marqueurs « à vérifier » sur phases
    c1col = "Hallstatt C1 (800-660)"
    if c1col in df.columns:
        anomalies["phase_a_verifier"] += df[c1col].astype(str).str.contains(
            "vérifier|verifier", case=False, na=False
        ).sum()

    # T3 — type_site
    def row_type_site(row: pd.Series) -> str:
        t1 = any(is_tertre_signal(row.get(c)) for c in TERTRE_COLS if c in row.index)
        return "tumulus" if t1 else "nécropole"

    df["type_site"] = df.apply(row_type_site, axis=1)

    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

    def to_wgs84(x: float | None, y: float | None) -> tuple[float | None, float | None]:
        if x is None or y is None or coord_outlier_xy(x, y):
            return None, None
        lon, lat = transformer.transform(float(x), float(y))
        return float(lon), float(lat)

    lons, lats = [], []
    for i in df.index:
        lo, la = to_wgs84(df.at[i, "x_l93"], df.at[i, "y_l93"])
        lons.append(lo)
        lats.append(la)
    df["longitude"] = lons
    df["latitude"] = lats

    # Charger sites.csv pour T5
    existing: pd.DataFrame | None = None
    existing_by_site: dict[str, dict] = {}
    necro_marker = "20250324_necropoles_BFIIIb-HaD3_Als-Lor"
    if SITES_CSV.is_file():
        existing = pd.read_csv(SITES_CSV)
        for sid, g in existing.groupby("site_id"):
            r0 = g.iloc[0]
            try:
                ex = float(r0["x_l93"])
                ey = float(r0["y_l93"])
            except (TypeError, ValueError):
                ex, ey = float("nan"), float("nan")
            existing_by_site[str(sid)] = {
                "x_l93": ex,
                "y_l93": ey,
                "commune": str(r0.get("commune", "") or ""),
                "nom_site": str(r0.get("nom_site", "") or ""),
                "refs": " ".join(g["source_references"].astype(str)),
            }

    def find_spatial_name_matches(
        commune_out: str,
        nom_out: str,
        x: float | None,
        y: float | None,
    ) -> list[tuple[str, float, str]]:
        """Liste (site_id, distance_m, raison)."""
        if existing is None or not existing_by_site:
            return []
        cnorm = commune_out or ""
        nnorm = nom_out or ""
        out: list[tuple[str, float, str]] = []
        strict_nom = ascii_fold(nnorm)
        strict_com = ascii_fold(cnorm)

        for sid, info in existing_by_site.items():
            ex, ey = info["x_l93"], info["y_l93"]
            r_commune = info["commune"]
            r_nom = info["nom_site"]

            if strict_com and strict_nom:
                if ascii_fold(r_commune) == strict_com and ascii_fold(r_nom) == strict_nom:
                    d = (
                        dist_m(float(x), float(y), ex, ey)
                        if x is not None and y is not None and ex == ex and ey == ey
                        else 0.0
                    )
                    out.append((sid, d, "commune+nom strict"))

            if x is not None and y is not None and ex == ex and ey == ey:
                dxy = dist_m(float(x), float(y), ex, ey)
                if dxy <= MATCH_DIST_USED_M and commune_similar(cnorm, r_commune):
                    out.append((sid, dxy, f"distance<={MATCH_DIST_USED_M}m+commune"))

        # Dédupliquer par site_id en gardant distance min
        best: dict[str, tuple[float, str]] = {}
        for sid, d, reason in out:
            if sid not in best or d < best[sid][0]:
                best[sid] = (d, reason)
        return [(sid, best[sid][0], best[sid][1]) for sid in best]

    def necro_phase_already_in_base(site_id: str, per: str, sp_out: str) -> bool:
        if existing is None:
            return False
        sub = existing[
            (existing["site_id"].astype(str) == site_id)
            & (existing["periode"].astype(str) == per)
            & (existing["sous_periode"].fillna("").astype(str) == sp_out)
        ]
        if sub.empty:
            return False
        return bool(sub["source_references"].astype(str).str.contains(necro_marker, na=False).any())

    chronologie_col = "Chronologie et commentaires"
    biblio_col = "biblio"
    occ_col = "Occupation nécropole"

    phase_rows: list[dict] = []
    report_rows: list[dict] = []

    for idx, (_, row) in enumerate(df.iterrows()):
        ri = int(row.get("row_index", idx + 1)) if pd.notna(row.get("row_index")) else idx + 1
        commune_out = str(row.get("commune_norm") or row.get("Commune") or "").strip()
        nom_out = str(row.get("nom_site") or "").strip()
        x, y = row.get("x_l93"), row.get("y_l93")
        xs = float(x) if x is not None and x == x else None
        ys = float(y) if y is not None and y == y else None

        occ_raw = (
            collapse_spaces(str(row[occ_col]))
            if occ_col in row.index and pd.notna(row.get(occ_col))
            else ""
        )
        chrono = (
            collapse_spaces(str(row[chronologie_col]))
            if chronologie_col in row.index and pd.notna(row.get(chronologie_col))
            else ""
        )
        biblio = (
            collapse_spaces(str(row[biblio_col]))
            if biblio_col in row.index and pd.notna(row.get(biblio_col))
            else ""
        )
        base_ref = SOURCE_REF_REL + (f";{biblio}" if biblio else "")

        phases_from_binary: list[tuple[str, str, str | None, int | None, int | None]] = []
        for col, per, sous, dd, df_ in PHASE_COLUMN_SPECS:
            if col not in row.index:
                continue
            if is_phase_column_active(row[col]):
                ddf, dff = dd, df_
                # Bornes référentiel uniquement pour sous-périodes D (pas Ha C : colonnes Excel plus fines)
                if sous in ("Ha D1", "Ha D2", "Ha D3") and periodes_cfg:
                    p2, d2 = apply_sous_periode_dates(per, sous, periodes_cfg)
                    if p2 is not None and d2 is not None:
                        ddf, dff = p2, d2
                phases_from_binary.append((per, sous, sous, ddf, dff))

        text_phases: list[tuple[str, str, str | None, int | None, int | None]] = []
        ptxt, stxt, ddtxt, dftxt, note = parse_periode_from_text(
            row.get("Datation"), row.get(occ_col), periodes_cfg
        )
        if ptxt != "indéterminé" or stxt:
            d1, d2 = ddtxt, dftxt
            if stxt and (d1 is None and d2 is None):
                d1, d2 = apply_sous_periode_dates(ptxt, stxt, periodes_cfg)
            label = stxt or ptxt
            text_phases.append((ptxt, stxt, label, d1, d2))

        if phases_from_binary:
            merged: dict[tuple[str, str | None], tuple[int | None, int | None, str]] = {}
            for per, sous, label, dda, dfa in phases_from_binary:
                key = (per, sous)
                merged[key] = (dda, dfa, label)
            for per, sous, label, dda, dfa in text_phases:
                key = (per, sous)
                if key not in merged:
                    merged[key] = (dda, dfa, label)
            final_phases = [(p, s, merged[(p, s)][2], merged[(p, s)][0], merged[(p, s)][1]) for p, s in merged]
        elif text_phases:
            final_phases = text_phases
        else:
            final_phases = [("indéterminé", None, None, None, None)]

        sous_vals = {s for _, s, _, _, _ in final_phases if s}
        if any(x in sous_vals for x in ("Ha D1", "Ha D2", "Ha D3")):
            final_phases = [fp for fp in final_phases if not (fp[0] == "Hallstatt" and fp[1] in (None, "Ha D"))]

        matches = find_spatial_name_matches(commune_out, nom_out, xs, ys)
        matches.sort(key=lambda t: t[1])

        chosen_site_id: str | None = None
        match_reason = ""
        action_site = "new"
        if len(matches) == 1:
            chosen_site_id = matches[0][0]
            match_reason = matches[0][2]
            action_site = "merge"
        elif len(matches) > 1:
            action_site = "review"
            match_reason = "plusieurs candidats: " + ",".join(m[0] for m in matches[:5])

        if action_site == "review":
            chosen_site_id = new_site_id(commune_out, nom_out, xs, ys, ri)
        elif action_site == "new" or chosen_site_id is None:
            chosen_site_id = new_site_id(commune_out, nom_out, xs, ys, ri)
            match_reason = match_reason or "aucune correspondance"

        for pidx, (per, sous, label, ddb, dfe) in enumerate(final_phases):
            sp_out = sous if sous is not None else ""
            dd_s = "" if ddb is None else str(ddb)
            df_s = "" if dfe is None else str(dfe)

            skip_dup = action_site == "merge" and necro_phase_already_in_base(chosen_site_id, per, sp_out)

            phase_action = "skip_duplicate" if skip_dup else ("merge" if action_site == "merge" else "new")
            if action_site == "review":
                phase_action = "review"

            pid = new_phase_id(chosen_site_id, sp_out or label or per, ddb, dfe, ri, pidx)

            report_rows.append(
                {
                    "row_index": ri,
                    "excel_row_ordinal": idx,
                    "commune": commune_out,
                    "nom_site": nom_out,
                    "phase_index": pidx,
                    "action": phase_action,
                    "site_id": chosen_site_id,
                    "matched_reason": match_reason,
                    "coord_quality": row.get("coord_quality"),
                    "periode": per,
                    "sous_periode": sp_out,
                }
            )

            if phase_action == "skip_duplicate":
                continue

            src_count = len([p for p in base_ref.split(";") if p.strip()])

            phase_rows.append(
                {
                    "site_id": chosen_site_id,
                    "nom_site": nom_out,
                    "commune": commune_out,
                    "pays": "FR",
                    "type_site": row["type_site"],
                    "x_l93": xs if xs is not None else "",
                    "y_l93": ys if ys is not None else "",
                    "longitude": row["longitude"] if pd.notna(row["longitude"]) else "",
                    "latitude": row["latitude"] if pd.notna(row["latitude"]) else "",
                    "phase_id": pid,
                    "periode": per,
                    "sous_periode": sp_out,
                    "datation_debut": dd_s,
                    "datation_fin": df_s,
                    "sources_count": src_count,
                    "source_references": base_ref,
                    "occupation_necropole_raw": occ_raw,
                    "chronologie_comment": " | ".join(
                        filter(None, [chrono, note, (f"parse:{label}" if label and not sp_out else "")])
                    ).strip(" |")
                    or chrono,
                }
            )

    out_df = pd.DataFrame(phase_rows)
    rep_df = pd.DataFrame(report_rows)

    # Sauvegarde ancien sites_cleaned
    if OUT_CLEANED.is_file():
        backup = REPO_ROOT / "data/output" / BACKUP_SUFFIX
        shutil.copy2(OUT_CLEANED, backup)

    OUT_CLEANED.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_CLEANED, index=False, encoding="utf-8")
    rep_df.to_csv(OUT_REPORT, index=False, encoding="utf-8")

    # Résumé
    n_src = len(df)
    n_phase_out = len(out_df)
    n_rep = len(rep_df)
    act_counts = rep_df["action"].value_counts().to_dict() if n_rep else {}

    print(f"Source: {src_path}")
    print(f"Lignes source (Excel): {n_src}")
    print(f"Lignes phases exportées (sites_cleaned): {n_phase_out}")
    print(f"Lignes rapport (ingest_report): {n_rep}")
    print(f"Actions: {act_counts}")
    print(f"Anomalies: {anomalies}")
    print(f"Export: {OUT_CLEANED}")
    print(f"Rapport: {OUT_REPORT}")


if __name__ == "__main__":
    main()
