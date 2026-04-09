#!/usr/bin/env python3
"""Ingestion T1–T6 : 20240419_Inhumations silos (1).xlsx → sites_cleaned + détail.

Fusion idempotente dans data/output/sites_cleaned.csv (suppression des lignes
provenant du même fichier source avant réécriture).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
PATH_INPUT = ROOT / "data" / "input" / "20240419_Inhumations silos (1).xlsx"
REF_TYPES = ROOT / "data" / "reference" / "types_sites.json"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
PATH_EXISTING_SITES = ROOT / "data" / "output" / "sites.csv"
PATH_SITES_CLEANED = ROOT / "data" / "output" / "sites_cleaned.csv"
OUT_DIR = ROOT / "data" / "output" / "ingest"
SOURCE_FILE_REL = "data/input/20240419_Inhumations silos (1).xlsx"
SOURCE_MARKER = "20240419_Inhumations silos"

FR_DEPTS = {"67", "68", "57", "54"}

PERIODE_DISPLAY = {
    "HALLSTATT": "Hallstatt",
    "LA_TENE": "La Tène",
    "TRANSITION": "Transition",
    "INDETERMINE": "indéterminé",
}


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


def canonical_commune(raw: str | float | None, toponyme_map: dict[str, str]) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    return toponyme_map.get(normalize_text(s), s)


def parse_float_coord(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().replace(",", ".")
    if not s or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build_sous_date_index(periodes: dict) -> dict[str, tuple[int, int]]:
    """Nom de sous-période (exact JSON) → (debut, fin)."""
    out: dict[str, tuple[int, int]] = {}
    for pname, pdata in periodes.items():
        if pname == "TRANSITION":
            for sp, spdef in pdata.get("sous_periodes", {}).items():
                out[sp] = (spdef["date_debut"], spdef["date_fin"])
        else:
            for sp, spdef in pdata.get("sous_periodes", {}).items():
                out[sp] = (spdef["date_debut"], spdef["date_fin"])
    return out


def span_subperiods(names: list[str], sous_idx: dict[str, tuple[int, int]], periodes: dict) -> tuple[int, int]:
    """Plus petite date_debut et plus grande date_fin parmi les sous-périodes connues."""
    ds: list[int] = []
    fs: list[int] = []
    for n in names:
        if n in sous_idx:
            a, b = sous_idx[n]
            ds.append(a)
            fs.append(b)
    if not ds:
        return 0, 0
    return min(ds), max(fs)


def normalize_datation_string(raw: str) -> str:
    t = raw.replace("\xa0", " ").strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(?i)\bltb\b", "LT B", t)
    t = re.sub(r"(?i)\blta\b", "LT A", t)
    t = re.sub(r"(?i)\bltc\b", "LT C", t)
    t = re.sub(r"(?i)\bltd\b", "LT D", t)
    t = re.sub(r"Ha\s*D\s*3", "Ha D3", t, flags=re.I)
    t = re.sub(r"Ha\s*D\s*1", "Ha D1", t, flags=re.I)
    t = re.sub(r"Ha\s*D\s*2", "Ha D2", t, flags=re.I)
    t = re.sub(r"Ha\s*C", "Ha C", t, flags=re.I)
    t = re.sub(r"LT\s*", "LT ", t, flags=re.I)
    return t.strip()


def parse_datation_relative(
    datation_raw: str | float | None,
    periodes: dict,
    sous_idx: dict[str, tuple[int, int]],
) -> tuple[str, str | None, int | None, int | None, str]:
    """
    Retourne (periode_key, sous_periode, datation_debut, datation_fin, periode_display).
    periode_key ∈ HALLSTATT | LA_TENE | TRANSITION | INDETERMINE
    """
    if datation_raw is None or (isinstance(datation_raw, float) and pd.isna(datation_raw)):
        return "INDETERMINE", None, None, None, "indéterminé"

    raw0 = str(datation_raw).replace("\xa0", " ").strip()
    if not raw0 or raw0.lower() == "nan":
        return "INDETERMINE", None, None, None, "indéterminé"

    low = raw0.lower()
    if low in ("datation relative", "idem 1017a-b"):
        return "INDETERMINE", None, None, None, "indéterminé"

    if any(
        x in low
        for x in (
            "bronze final",
            "bz fin",
            "bz final",
            "néolithique",
            "epoque historique",
            "historique",
            "attention : cette fosse",
        )
    ):
        return "INDETERMINE", None, None, None, "indéterminé"

    s = normalize_datation_string(raw0)
    s_compact = re.sub(r"\s+", "", s)
    s_low = s.lower()

    tr_sp = "Ha D3 / LT A"
    tr_def = periodes["TRANSITION"]["sous_periodes"][tr_sp]
    tr_d0, tr_d1 = tr_def["date_debut"], tr_def["date_fin"]

    # Règles explicites (ordre : motifs les plus spécifiques d'abord)
    rules: list[tuple[bool, tuple[str, str | None, int | None, int | None, str]]] = [
        (
            bool(re.search(r"Ha\s*D3\s*[-/]\s*LT\s*A\d?", s, re.I) or re.search(r"Ha\s*D3/LTA", s_compact, re.I)),
            ("TRANSITION", tr_sp, tr_d0, tr_d1, "Transition"),
        ),
        (
            "Ha D3-LTA2" in s_compact or "Ha D3-LTA 2" in s_compact.replace(" ", ""),
            ("TRANSITION", tr_sp, tr_d0, tr_d1, "Transition"),
        ),
        (
            bool(re.match(r"^Ha\s*C\s*[-/]\s*LT\s*A", s, re.I)),
            ("TRANSITION", tr_sp, tr_d0, tr_d1, "Transition"),
        ),
        (
            bool(re.match(r"^Ha\s*C\s*[-/]\s*Ha\s*D3", s, re.I)),
            (
                "HALLSTATT",
                "Ha C",
                *span_subperiods(["Ha C", "Ha D3"], sous_idx, periodes),
                "Hallstatt",
            ),
        ),
        (
            bool(re.search(r"Ha\s*C\s*[-/]\s*D1", s, re.I))
            or bool(re.search(r"HaC[-/]D1", s_compact, re.I))
            or "hallstatt c-d1" in s_low
            or "hallstatt c-d2" in s_low,
            (
                "HALLSTATT",
                "Ha C",
                *span_subperiods(["Ha C", "Ha D1"], sous_idx, periodes),
                "Hallstatt",
            ),
        ),
        (
            bool(re.match(r"^Ha\s*D1\s*[-/]\s*D2", s, re.I)),
            (
                "HALLSTATT",
                "Ha D1",
                *span_subperiods(["Ha D1", "Ha D2"], sous_idx, periodes),
                "Hallstatt",
            ),
        ),
        (
            bool(re.match(r"^LT\s*B1\s*[-/]\s*C1", s, re.I) or "ltb1-ltc1" in s_low.replace(" ", "")),
            (
                "LA_TENE",
                "LT B1",
                *span_subperiods(["LT B1", "LT C1"], sous_idx, periodes),
                "La Tène",
            ),
        ),
        (
            bool(re.match(r"^LT\s*A2\s*[-/]\s*B1", s, re.I)),
            (
                "LA_TENE",
                "LT A",
                *span_subperiods(["LT A", "LT B1"], sous_idx, periodes),
                "La Tène",
            ),
        ),
        (
            bool(re.match(r"^LT\s*A\s*[-/]\s*B", s, re.I)),
            (
                "LA_TENE",
                "LT A",
                *span_subperiods(["LT A"], sous_idx, periodes),
                "La Tène",
            ),
        ),
        (
            bool(re.match(r"^LT\s*B\s*[-/]\s*C", s, re.I) or "la tène b-c1" in s_low),
            (
                "LA_TENE",
                "LT B1",
                *span_subperiods(["LT B1", "LT C1"], sous_idx, periodes),
                "La Tène",
            ),
        ),
        (
            bool(re.match(r"^LT\s*C2\s*[-/]\s*D2", s, re.I)),
            (
                "LA_TENE",
                "LT C2",
                *span_subperiods(["LT C2", "LT D2"], sous_idx, periodes),
                "La Tène",
            ),
        ),
        (
            bool(re.match(r"^LT\s*C1\s*$", s, re.I)),
            ("LA_TENE", "LT C1", *sous_idx["LT C1"], "La Tène"),
        ),
        (
            bool(re.match(r"^LT\s*B\s*$", s, re.I)),
            (
                "LA_TENE",
                "LT B",
                sous_idx["LT B1"][0],
                sous_idx["LT B2"][1],
                "La Tène",
            ),
        ),
        (
            bool(re.match(r"^LT\s*A\s*$", s, re.I)),
            ("LA_TENE", "LT A", *sous_idx["LT A"], "La Tène"),
        ),
        (
            bool(re.match(r"^Ha\s*D3\s*$", s, re.I)),
            ("HALLSTATT", "Ha D3", *sous_idx["Ha D3"], "Hallstatt"),
        ),
        (
            bool(re.match(r"^Ha\s*D1\s*$", s, re.I)),
            ("HALLSTATT", "Ha D1", *sous_idx["Ha D1"], "Hallstatt"),
        ),
        (
            bool(re.match(r"^Ha\s*D\s*$", s, re.I)),
            (
                "HALLSTATT",
                "Ha D",
                sous_idx["Ha D1"][0],
                sous_idx["Ha D3"][1],
                "Hallstatt",
            ),
        ),
        (
            bool(re.match(r"^Ha\s*C\s*$", s, re.I)) or re.match(r"^Hallstatt\s*C\d?", s, re.I),
            ("HALLSTATT", "Ha C", *sous_idx["Ha C"], "Hallstatt"),
        ),
        (
            "hallstatt c1-c2" in s_low,
            ("HALLSTATT", "Ha C", *sous_idx["Ha C"], "Hallstatt"),
        ),
        (
            bool(re.match(r"^Hallstatt\s*D1", s, re.I)),
            ("HALLSTATT", "Ha D1", *sous_idx["Ha D1"], "Hallstatt"),
        ),
        (
            low == "hallstatt",
            (
                "HALLSTATT",
                None,
                periodes["HALLSTATT"]["date_debut"],
                periodes["HALLSTATT"]["date_fin"],
                "Hallstatt",
            ),
        ),
    ]

    for cond, tup in rules:
        if cond:
            pk, sp, d0, d1, disp = tup
            if d0 == 0 and d1 == 0:
                return "INDETERMINE", None, None, None, "indéterminé"
            return pk, sp, d0, d1, disp

    # Fallback : regex sous-périodes + logique Ha/LT
    sub_re = re.compile(
        r"Ha\s*[CD](?:\d)?(?:\s*[-/]\s*[CD]?\d)?|LT\s*[A-D](?:\d)?",
        re.I,
    )
    matches = sub_re.findall(s)
    if not matches:
        return "INDETERMINE", None, None, None, "indéterminé"

    def norm_token(tok: str) -> str:
        t = tok.strip()
        t = re.sub(r"\s+", " ", t)
        m = re.match(r"^(LT)\s*([A-D]\d?)$", t, re.I)
        if m:
            return f"{m.group(1).upper()} {m.group(2).upper()}"
        m = re.match(r"^(Ha)\s*([CD]\d?)$", t, re.I)
        if m:
            return f"{m.group(1)} {m.group(2).upper()}"
        return t

    tokens = [norm_token(m) for m in matches]
    has_ha = any(re.match(r"^Ha\b", t, re.I) for t in tokens)
    has_lt = any(re.match(r"^LT\b", t, re.I) for t in tokens)

    if has_ha and has_lt:
        return "TRANSITION", tr_sp, tr_d0, tr_d1, "Transition"

    resolved: list[str] = []
    for t in tokens:
        if re.match(r"^Ha\s*D$", t, re.I):
            resolved.extend(["Ha D1", "Ha D2", "Ha D3"])
        elif t in sous_idx:
            resolved.append(t)
        else:
            sp, _, _ = _fuzzy_sous(t, periodes)
            if sp:
                resolved.append(sp)

    if not resolved:
        return "INDETERMINE", None, None, None, "indéterminé"

    if has_lt and not has_ha:
        d0, d1 = span_subperiods(resolved, sous_idx, periodes)
        sp0 = resolved[0]
        return "LA_TENE", sp0, d0, d1, "La Tène"

    d0, d1 = span_subperiods(resolved, sous_idx, periodes)
    sp0 = resolved[0]
    return "HALLSTATT", sp0, d0, d1, "Hallstatt"


def _fuzzy_sous(token: str, periodes: dict) -> tuple[str | None, int | None, int | None]:
    t_compact = re.sub(r"\s+", "", token)
    for pname, pdata in periodes.items():
        if pname == "TRANSITION":
            continue
        for sp_name, sp_data in pdata.get("sous_periodes", {}).items():
            if re.sub(r"\s+", "", sp_name) == t_compact:
                return sp_name, sp_data["date_debut"], sp_data["date_fin"]
    return None, None, None


def site_id_from_key(key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"SITE-{h}"


def phase_id_stable(site_id: str, periode_disp: str, sous: str | None, d0, d1) -> str:
    sp = sous or ""
    payload = f"{site_id}|{periode_disp}|{sp}|{d0}|{d1}|{SOURCE_MARKER}"
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"SITE-{h}-PH1"


def dist_l93(x1, y1, x2, y2) -> float:
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return float("inf")
    if any(pd.isna(v) for v in (x1, y1, x2, y2)):
        return float("inf")
    dx = float(x1) - float(x2)
    dy = float(y1) - float(y2)
    return (dx * dx + dy * dy) ** 0.5


def dept_pays(d) -> str:
    s = str(d).strip() if pd.notna(d) else ""
    if s in FR_DEPTS:
        return "FR"
    return ""


def build_nom_site(row) -> str:
    site = str(row["Site"]).strip() if pd.notna(row["Site"]) else ""
    ld = str(row["Lieu dit"]).strip() if pd.notna(row["Lieu dit"]) else ""
    ld = ld.replace("\n", " ").strip()
    if not ld or normalize_text(ld) == normalize_text(site):
        return site
    return f"{site} - {ld}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    with open(REF_TYPES, encoding="utf-8") as f:
        types_ref = json.load(f)
    assert "NECROPOLE" in types_ref.get("aliases", {}), "types_sites.json : NECROPOLE requis"

    with open(REF_PERIODES, encoding="utf-8") as f:
        periodes_ref = json.load(f)
    periodes = periodes_ref["periodes"]
    sous_idx = build_sous_date_index(periodes)

    toponyme_map = load_toponyme_map(REF_TOPONYMES)
    type_site_out = "nécropole"

    print("=== T1 — Chargement ===")
    df = pd.read_excel(PATH_INPUT, engine="openpyxl", header=0, dtype=str, sheet_name=0)
    df.columns = df.columns.str.replace(r"\s+", " ", regex=True).str.strip()
    n_raw = len(df)
    print(f"Lignes brutes : {n_raw}")

    if "Unnamed: 93" in df.columns:
        df = df.rename(columns={"Unnamed: 93": "notes_datation"})

    key_cols = [
        "Département",
        "Site",
        "Lieu dit",
        "X(L93)",
        "Y(L93)",
        "Datation relative",
    ]
    for c in df.columns:
        if c in key_cols or c == "notes_datation":
            df[c] = df[c].replace(r"^\s*$", pd.NA, regex=True)
            df[c] = df[c].replace(" ", pd.NA)

    print("=== T2 — Nettoyage ===")
    dep_u = df["Département"].fillna("").str.upper()
    site_s = df["Site"].fillna("")
    lieu_s = df["Lieu dit"].fillna("")
    mask_total = (dep_u != "TOTAL") & (~site_s.str.contains("TOTAL", case=False, na=False)) & (
        ~lieu_s.str.contains("TOTAL", case=False, na=False)
    )
    mask_junk = ~df["Département"].fillna("").isin(["Supprimé", "Département"])
    mask_not_header_echo = ~((df["Département"] == "Département") & (df["Site"] == "Site"))
    mask_not_blank = ~(df["Département"].isna() & df["Site"].isna())
    n_dropped_total = int((~mask_total).sum())
    n_dropped_blank = int((mask_total & mask_junk & mask_not_header_echo & (~mask_not_blank)).sum())
    df = df.loc[mask_total & mask_junk & mask_not_header_echo & mask_not_blank].copy()
    df.reset_index(drop=True, inplace=True)
    n_after_clean = len(df)
    print(f"Lignes après filtre TOTAL / en-têtes / lignes vides : {n_after_clean}")
    if n_dropped_total:
        warnings.append(f"{n_dropped_total} ligne(s) « TOTAL » ou contenant TOTAL exclues.")
    if n_dropped_blank:
        warnings.append(f"{n_dropped_blank} ligne(s) sans Département ni Site exclues (lignes vides Excel).")

    xs = df["X(L93)"].map(parse_float_coord)
    ys = df["Y(L93)"].map(parse_float_coord)
    df["x_l93"] = xs
    df["y_l93"] = ys
    df["has_coords"] = df["x_l93"].notna() & df["y_l93"].notna()

    def coord_flag_row(r) -> str | float:
        if not r["has_coords"]:
            return pd.NA
        x, y = r["x_l93"], r["y_l93"]
        if not (900_000 <= x <= 1_300_000 and 6_100_000 <= y <= 7_200_000):
            return "out_of_range"
        return pd.NA

    df["coord_flag"] = df.apply(coord_flag_row, axis=1)
    n_out = int(df["coord_flag"].notna().sum())
    if n_out:
        warnings.append(f"{n_out} ligne(s) avec coordonnées L93 hors plausibilité (coord_flag).")

    print("=== T3 — Classification ===")
    df["pays"] = df["Département"].map(dept_pays)
    df["commune"] = df["Site"].map(lambda s: canonical_commune(s, toponyme_map))
    df["nom_site"] = df.apply(build_nom_site, axis=1)
    df["type_site"] = type_site_out

    parsed = df["Datation relative"].map(lambda x: parse_datation_relative(x, periodes, sous_idx))
    df["periode_key"] = parsed.map(lambda t: t[0])
    df["sous_periode"] = parsed.map(lambda t: t[1])
    df["datation_debut"] = parsed.map(lambda t: t[2])
    df["datation_fin"] = parsed.map(lambda t: t[3])
    df["periode"] = parsed.map(lambda t: t[4])

    print("=== T4 — Projection L93 → WGS84 ===")
    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
    lons, lats = [], []
    for _, r in df.iterrows():
        if r["has_coords"]:
            lo, la = transformer.transform(float(r["x_l93"]), float(r["y_l93"]))
            lons.append(lo)
            lats.append(la)
        else:
            lons.append(None)
            lats.append(None)
    df["longitude"] = lons
    df["latitude"] = lats

    df["lieu_dit_norm"] = df["Lieu dit"].map(normalize_text)
    df["commune_norm"] = df["commune"].map(normalize_text)

    def agg_key_row(r) -> str:
        if r["has_coords"]:
            xr = int(round(float(r["x_l93"]) / 50.0)) * 50
            yr = int(round(float(r["y_l93"]) / 50.0)) * 50
        else:
            xr, yr = "noc", "noc"
        return f"{r['commune_norm']}|{r['lieu_dit_norm']}|{xr}|{yr}"

    df["agg_key"] = df.apply(agg_key_row, axis=1)

    print("=== T5 — Agrégation site × phase & déduplication ===")
    ex = pd.read_csv(PATH_EXISTING_SITES, dtype=str, low_memory=False)
    ex_u = ex.drop_duplicates(subset=["site_id"], keep="first").copy()
    ex_u["x_l93_f"] = pd.to_numeric(ex_u["x_l93"], errors="coerce")
    ex_u["y_l93_f"] = pd.to_numeric(ex_u["y_l93"], errors="coerce")
    ex_u["commune_norm"] = ex_u["commune"].map(normalize_text)
    ex_u["nom_norm"] = ex_u["nom_site"].map(normalize_text)

    # site_id par agg_key (même pour toutes les phases du site)
    agg_site_ids: dict[str, str] = {}
    agg_match_info: dict[str, dict] = {}

    for key, g in df.groupby("agg_key", sort=False):
        first = g.iloc[0]
        x_med = g["x_l93"].dropna().median() if g["x_l93"].notna().any() else None
        y_med = g["y_l93"].dropna().median() if g["y_l93"].notna().any() else None
        has_c = x_med is not None and y_med is not None and pd.notna(x_med) and pd.notna(y_med)
        x_out = float(x_med) if has_c else None
        y_out = float(y_med) if has_c else None

        nom_site_g = str(first["nom_site"])
        commune_g = str(first["commune"])
        norm_comm = normalize_text(commune_g)
        norm_nom = normalize_text(nom_site_g)

        candidates: list[dict] = []
        for _, er in ex_u.iterrows():
            same_comm = bool(norm_comm and er["commune_norm"] == norm_comm)
            dist = dist_l93(x_out, y_out, er["x_l93_f"], er["y_l93_f"])
            same_name = bool(norm_nom and er["nom_norm"] == norm_nom)
            if (same_comm and has_c and dist < 100) or same_name:
                candidates.append(
                    {
                        "site_id": er["site_id"],
                        "dist_m": float(dist) if dist != float("inf") else None,
                        "same_commune_100m": bool(same_comm and has_c and dist < 100),
                        "same_nom": bool(same_name),
                    }
                )

        merge_candidate = len(candidates) > 1
        match_id: str | None = None
        if candidates:
            candidates.sort(key=lambda c: (c["dist_m"] is None, c["dist_m"] or 1e18))
            match_id = str(candidates[0]["site_id"])
        is_new = match_id is None
        new_site_id = match_id if match_id else site_id_from_key(key + "|inhumations_silos")

        agg_site_ids[key] = new_site_id
        agg_match_info[key] = {
            "match_existing_site_id": match_id,
            "is_new": is_new,
            "merge_candidate": merge_candidate,
            "candidates": candidates,
            "x_l93": x_out,
            "y_l93": y_out,
            "has_coords": has_c,
            "nom_site": nom_site_g,
            "commune": commune_g,
            "pays": str(first["pays"]) if first["pays"] else "FR",
        }
        if merge_candidate:
            warnings.append(f"Clé {key[:48]}… : plusieurs candidats sites.csv (merge_candidate).")

    df["site_id_resolved"] = df["agg_key"].map(agg_site_ids)

    n_unique_sites = len(agg_site_ids)
    n_matched = sum(1 for k, v in agg_match_info.items() if v["match_existing_site_id"])
    n_new = sum(1 for k, v in agg_match_info.items() if v["is_new"])
    print(f"Sites uniques (clés d'agrégation) : {n_unique_sites}")
    print(f"  Correspondance inventaire sites.csv : {n_matched}")
    print(f"  Nouveaux site_id générés : {n_new}")

    # Lignes export sites_cleaned : une par site × phase
    export_rows: list[dict] = []
    phase_groups = df.groupby(["agg_key", "periode", "sous_periode", "datation_debut", "datation_fin"], dropna=False)
    for (akey, periode_disp, sous, d0, d1), g in phase_groups:
        info = agg_match_info[akey]
        site_id = agg_site_ids[akey]
        sous_s = "" if sous is None or (isinstance(sous, float) and pd.isna(sous)) else str(sous)
        d0i = int(d0) if d0 is not None and pd.notna(d0) else None
        d1i = int(d1) if d1 is not None and pd.notna(d1) else None
        phase_id = phase_id_stable(site_id, str(periode_disp), sous_s or None, d0i, d1i)

        raw_chronos = sorted({str(x).strip() for x in g["Datation relative"].dropna() if str(x).strip()})
        chronologie_comment = "; ".join(raw_chronos[:12])
        if len(raw_chronos) > 12:
            chronologie_comment += " …"

        has_c = info["has_coords"]
        xo, yo = info["x_l93"], info["y_l93"]
        lo = la = None
        if has_c and xo is not None and yo is not None:
            lo, la = transformer.transform(float(xo), float(yo))

        rem_parts = []
        if g["coord_flag"].notna().any():
            rem_parts.append("coord hors plage sur au moins une ligne source")
        if info.get("merge_candidate"):
            rem_parts.append("plusieurs correspondances sites.csv")
        remarques = " | ".join(rem_parts)

        export_rows.append(
            {
                "site_id": site_id,
                "nom_site": info["nom_site"],
                "commune": info["commune"],
                "pays": info["pays"],
                "type_site": type_site_out,
                "x_l93": xo if has_c else "",
                "y_l93": yo if has_c else "",
                "longitude": lo if has_c and lo is not None else "",
                "latitude": la if has_c and la is not None else "",
                "phase_id": phase_id,
                "periode": periode_disp,
                "sous_periode": sous_s,
                "datation_debut": d0i if d0i is not None else "",
                "datation_fin": d1i if d1i is not None else "",
                "sources_count": len(g),
                "source_references": SOURCE_FILE_REL,
                "occupation_necropole_raw": "inhumations en silo",
                "chronologie_comment": chronologie_comment,
                "source_file": SOURCE_FILE_REL,
                "armement_summary": "",
                "or_summary": "",
                "remarques": remarques,
            }
        )

    new_sites_df = pd.DataFrame(export_rows)
    cols_order = [
        "site_id",
        "nom_site",
        "commune",
        "pays",
        "type_site",
        "x_l93",
        "y_l93",
        "longitude",
        "latitude",
        "phase_id",
        "periode",
        "sous_periode",
        "datation_debut",
        "datation_fin",
        "sources_count",
        "source_references",
        "occupation_necropole_raw",
        "chronologie_comment",
        "source_file",
        "armement_summary",
        "or_summary",
        "remarques",
    ]
    new_sites_df = new_sites_df[cols_order]

    print("=== T6 — Export ===")
    detail_path = OUT_DIR / "inhumations_silos_detail.csv"
    df.to_csv(detail_path, index=False, encoding="utf-8")
    print(f"Détail individuel : {detail_path} ({len(df)} lignes)")

    log_path = OUT_DIR / "inhumations_silos_dedup_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source_file": SOURCE_FILE_REL,
                "reference_sites_csv": str(PATH_EXISTING_SITES.relative_to(ROOT)),
                "aggregated_site_keys": list(agg_match_info.keys()),
                "matches": [{**{"agg_key": k}, **{kk: vv for kk, vv in v.items() if kk != "candidates"}} for k, v in agg_match_info.items()],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Journal dédup : {log_path}")

    if PATH_SITES_CLEANED.exists():
        existing_clean = pd.read_csv(PATH_SITES_CLEANED, dtype=str, low_memory=False)
        mask_keep = ~existing_clean["source_file"].fillna("").str.contains(SOURCE_MARKER, regex=False, na=False)
        n_removed = int((~mask_keep).sum())
        merged = pd.concat([existing_clean.loc[mask_keep], new_sites_df], ignore_index=True)
        print(f"sites_cleaned : retrait de {n_removed} ligne(s) existantes liées à cette source, ajout de {len(new_sites_df)} ligne(s).")
    else:
        merged = new_sites_df
        warnings.append("sites_cleaned.csv absent : création avec uniquement les lignes de cette ingestion.")

    merged.to_csv(PATH_SITES_CLEANED, index=False, encoding="utf-8")
    print(f"Fichier fusionné : {PATH_SITES_CLEANED} ({len(merged)} lignes)")

    print("\n=== Résumé ===")
    print(f"Lignes brutes chargées : {n_raw}")
    print(f"Lignes après nettoyage : {n_after_clean}")
    print(f"Sites uniques (agrégation) : {n_unique_sites}")
    print(f"Sites appariés à l'inventaire : {n_matched}")
    print(f"Nouveaux sites : {n_new}")
    print(f"Lignes site×phase écrites : {len(new_sites_df)}")
    if warnings:
        print("Avertissements :")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
