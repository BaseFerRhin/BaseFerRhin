#!/usr/bin/env python3
"""
Ingestion « Alsace_Basel_AF » — feuille plate `sites` du XLSX (BaseFerRhin).
Pipeline T1–T6 : chargement, agrégation par id_site, inférences texte,
reprojection EPSG:4326 / EPSG:25832 → Lambert-93, dédup vs sites.csv + golden,
export sites_cleaned.csv + quality_report.json.

La colonne `date` du fichier n'est jamais utilisée comme chronologie archéologique.

Usage (depuis la racine du dépôt)::
    python scripts/ingest_alsace_basel_af.py
"""
from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pyproj import Transformer

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_XLSX = REPO_ROOT / "data/input/Alsace_Basel_AF (1).xlsx"
ANALYSIS_DIR = REPO_ROOT / "data/analysis/Alsace_Basel_AF (1)"
OUT_CLEANED = ANALYSIS_DIR / "sites_cleaned.csv"
OUT_REPORT = ANALYSIS_DIR / "quality_report.json"
REF_TYPES = REPO_ROOT / "data/reference/types_sites.json"
REF_PERIODES = REPO_ROOT / "data/reference/periodes.json"
REF_TOPONYMES = REPO_ROOT / "data/reference/toponymes_fr_de.json"
SITES_CSV = REPO_ROOT / "data/output/sites.csv"
GOLDEN_CSV = REPO_ROOT / "data/sources/golden_sites.csv"

EXPECTED_COLS = [
    "id_site",
    "pays",
    "admin1",
    "commune",
    "lieu_dit",
    "lieu_dit_autre",
    "x",
    "y",
    "epsg_coord",
    "decouverte_annee",
    "decouverte_operation",
    "ref_biblio",
    "ref_rapport",
    "auteur",
    "date",
    "commentaire",
]
SOURCE_TAG = "Alsace_Basel_AF_xlsx"
LON_MIN, LON_MAX = 5.0, 11.0
LAT_MIN, LAT_MAX = 45.0, 50.0
COORD_TOL = 1e-5
DEDUP_DISTANCE_M = 500.0
FUZZY_THRESHOLD = 0.85

PAYS_TO_CODE = {"France": "FR", "Suisse": "CH", "Allemagne": "DE"}

_transformer_4326_2154: Optional[Transformer] = None
_transformer_25832_2154: Optional[Transformer] = None
_transformer_25832_4326: Optional[Transformer] = None


def _t_4326_2154() -> Transformer:
    global _transformer_4326_2154
    if _transformer_4326_2154 is None:
        _transformer_4326_2154 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    return _transformer_4326_2154


def _t_25832_2154() -> Transformer:
    global _transformer_25832_2154
    if _transformer_25832_2154 is None:
        _transformer_25832_2154 = Transformer.from_crs("EPSG:25832", "EPSG:2154", always_xy=True)
    return _transformer_25832_2154


def _t_25832_4326() -> Transformer:
    global _transformer_25832_4326
    if _transformer_25832_4326 is None:
        _transformer_25832_4326 = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)
    return _transformer_25832_4326


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


def parse_float_cell(v: Any) -> Optional[float]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = float(v)
        return x if math.isfinite(x) else None
    t = collapse_spaces(str(v).replace(",", "."))
    if not t:
        return None
    try:
        x = float(t)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def parse_epsg(v: Any) -> Optional[int]:
    f = parse_float_cell(v)
    if f is None:
        return None
    i = int(round(f))
    if i in (4326, 25832):
        return i
    return None


def strip_text(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, datetime):
        return ""
    return collapse_spaces(str(v))


TYPE_CANON_TO_FR = {
    "oppidum": "oppidum",
    "habitat": "habitat",
    "necropole": "nécropole",
    "depot": "dépôt",
    "sanctuaire": "sanctuaire",
    "atelier": "atelier",
    "voie": "voie",
    "tumulus": "tumulus",
}


def load_excel_sites(path: Path) -> pd.DataFrame:
    """Lit la feuille `sites` (1083 × 16 attendu).

    Calamine en premier : certains classeurs ont une validation de données XML
    invalide qui fait échouer openpyxl ; openpyxl est essayé en repli.
    """
    kwargs = dict(io=str(path), sheet_name="sites", header=0)
    df = None
    last_err: Optional[Exception] = None
    for engine in ("calamine", "openpyxl"):
        try:
            df = pd.read_excel(**kwargs, engine=engine)
            break
        except Exception as exc:
            last_err = exc
            continue
    if df is None:
        raise RuntimeError(
            "Lecture XLSX impossible (calamine puis openpyxl). "
            "Installez python-calamine : pip install python-calamine"
        ) from last_err
    df.columns = df.columns.str.strip()
    if len(df.columns) != 16:
        raise SystemExit(f"Attendu 16 colonnes, obtenu {len(df.columns)}: {list(df.columns)}")
    return df


def wgs84_in_upper_rhine_bounds(lon: float, lat: float) -> bool:
    return LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def merge_unique_texts(*chunks: str, split_seps: str = ";,") -> str:
    seen: set[str] = set()
    out: list[str] = []
    for ch in chunks:
        if not ch:
            continue
        parts = re.split(r"[" + re.escape(split_seps) + r"]+", ch)
        for p in parts:
            s = collapse_spaces(p)
            if not s:
                continue
            key = ascii_fold(s)
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
    return " ; ".join(out)


def load_type_alias_patterns(path: Path) -> list[tuple[re.Pattern[str], str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    patterns: list[tuple[re.Pattern[str], str]] = []
    for canon, langs in (data.get("aliases") or {}).items():
        key = canon.lower()
        for lang in ("fr", "de"):
            for alias in langs.get(lang, []) or []:
                a = collapse_spaces(alias)
                if len(a) < 3:
                    continue
                patterns.append((re.compile(r"\b" + re.escape(a) + r"\b", re.I), key))
    patterns.sort(key=lambda x: -len(x[0].pattern))
    return patterns


def infer_type_site(text: str, patterns: list[tuple[re.Pattern[str], str]]) -> tuple[str, bool]:
    if not text.strip():
        return "indéterminé", False
    tl = text.lower()
    for rx, label in patterns:
        if rx.search(tl):
            return TYPE_CANON_TO_FR.get(label, label), True
    if re.search(r"\boppidum\b|fortification|enceinte|höhensiedlung", tl, re.I):
        return "oppidum", True
    if re.search(r"nécropole|tumulus|grabhügel|sépulture|inhumation", tl, re.I):
        return "nécropole", True
    if re.search(r"habitat|siedlung|ferme|fosse|cabane", tl, re.I):
        return "habitat", True
    if re.search(r"dépôt|hortfund|trésor|trouvaille", tl, re.I):
        return "dépôt", True
    if re.search(r"sanctuaire|heiligtum|fanum|kult", tl, re.I):
        return "sanctuaire", True
    if re.search(r"atelier|forge|schmiede|werkstatt", tl, re.I):
        return "atelier", True
    return "indéterminé", False


def load_periode_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_datation_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t.strip())
    t = re.sub(r"La\s*Tène", "La Tène", t, flags=re.I)
    return t


def infer_period_from_text(
    text: str, periodes_cfg: dict
) -> tuple[str, Optional[str], Optional[int], Optional[int], bool]:
    """Retourne (periode, sous_periode, dd, df, inferred)."""
    if not text or not text.strip():
        return "", None, None, None, False
    periodes = periodes_cfg.get("periodes", {})
    sub_re = periodes_cfg.get("sub_period_regex", "")
    raw = collapse_spaces(text)
    norm = normalize_datation_text(raw)
    tl = norm.lower()

    def match_patterns(cfg: dict, blob: str) -> bool:
        for p in cfg.get("patterns_fr", []) + cfg.get("patterns_de", []):
            if p and re.search(re.escape(p), blob, re.I):
                return True
        return False

    hall_cfg = periodes.get("HALLSTATT", {})
    lt_cfg = periodes.get("LA_TENE", {})
    trans_cfg = periodes.get("TRANSITION", {})

    is_ha = match_patterns(hall_cfg, norm) or bool(re.search(r"\bha\s*[cd]\d?", tl))
    is_lt = match_patterns(lt_cfg, norm) or bool(re.search(r"\blt\s*[a-d]\d?", tl))
    is_trans = match_patterns(trans_cfg, norm) or bool(
        re.search(r"ha\s*d3\s*[-/]\s*lt\s*a|d3\s*[-–]\s*lt\s*a|hallstatt.*lt\s*a", tl)
    )

    sous: Optional[str] = None
    if sub_re:
        m = re.findall(sub_re, norm, flags=re.I)
        if m:
            sous = re.sub(r"\s+", " ", m[-1].strip())
            if re.match(r"^ha\s", sous, re.I):
                sous = re.sub(r"^ha\s*", "Ha ", sous, flags=re.I)
            if re.match(r"^lt\s", sous, re.I):
                sous = re.sub(r"^lt\s*", "LT ", sous, flags=re.I)

    if is_trans or (is_ha and is_lt):
        sp = trans_cfg.get("sous_periodes", {}).get("Ha D3 / LT A", {})
        return "Hallstatt", "Ha D3 / LT A", sp.get("date_debut"), sp.get("date_fin"), True

    if is_lt and not is_ha:
        lt_subs = lt_cfg.get("sous_periodes", {})
        if sous:
            for k in lt_subs:
                if k.replace(" ", "").upper() in sous.replace(" ", "").upper():
                    sp = lt_subs[k]
                    return "La Tène", k, sp.get("date_debut"), sp.get("date_fin"), True
        return "La Tène", sous, lt_cfg.get("date_debut"), lt_cfg.get("date_fin"), True

    if is_ha:
        ha_subs = hall_cfg.get("sous_periodes", {})
        if sous:
            for k in ha_subs:
                if k.replace(" ", "").lower() in sous.replace(" ", "").lower():
                    sp = ha_subs[k]
                    return "Hallstatt", k, sp.get("date_debut"), sp.get("date_fin"), True
        return "Hallstatt", sous, hall_cfg.get("date_debut"), hall_cfg.get("date_fin"), True

    if re.search(r"hallstatt", tl):
        return "Hallstatt", sous, hall_cfg.get("date_debut"), hall_cfg.get("date_fin"), True
    if re.search(r"latène|la tène", tl):
        return "La Tène", sous, lt_cfg.get("date_debut"), lt_cfg.get("date_fin"), True

    return "", None, None, None, False


def fuzzy_token_sort_ratio(a: str, b: str) -> float:
    try:
        from rapidfuzz import fuzz

        return float(fuzz.token_sort_ratio(a, b)) / 100.0
    except Exception:
        ta = sorted(ascii_fold(a).split())
        tb = sorted(ascii_fold(b).split())
        if not ta and not tb:
            return 1.0
        if not ta or not tb:
            return 0.0
        sa, sb = set(ta), set(tb)
        inter = len(sa & sb)
        union = len(sa | sb)
        return inter / union if union else 0.0


def communes_compatible(a: str, b: str, variant_map: dict[str, str]) -> bool:
    ca, cb = normalize_commune(a, variant_map), normalize_commune(b, variant_map)
    if not ca or not cb:
        return False
    fa, fb = ascii_fold(ca), ascii_fold(cb)
    return fa == fb or fa in fb or fb in fa


def project_row(
    x: Optional[float], y: Optional[float], epsg: Optional[int]
) -> tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    bool,
    str,
]:
    """
    Retourne lon, lat, x_l93, y_l93, suspicious, note.
    Pas de transformation si EPSG inconnu ou coordonnées manquantes.
    """
    if x is None or y is None or epsg is None:
        return None, None, None, None, False, "missing_coords_or_epsg"

    suspicious = False
    if epsg == 4326:
        lon, lat = x, y
        if not wgs84_in_upper_rhine_bounds(lon, lat):
            suspicious = True
        try:
            x_l93, y_l93 = _t_4326_2154().transform(lon, lat)
        except Exception:
            return lon, lat, None, None, True, "reproj_4326_failed"
        return lon, lat, x_l93, y_l93, suspicious, "ok_4326"

    if epsg == 25832:
        try:
            lon, lat = _t_25832_4326().transform(x, y)
            x_l93, y_l93 = _t_25832_2154().transform(x, y)
        except Exception:
            return None, None, None, None, True, "reproj_25832_failed"
        if not wgs84_in_upper_rhine_bounds(lon, lat):
            suspicious = True
        return lon, lat, x_l93, y_l93, suspicious, "ok_25832"

    return None, None, None, None, False, "unknown_epsg"


def pick_coordinate_from_group(g: pd.DataFrame) -> tuple[
    Optional[float], Optional[float], Optional[int], bool, list[dict]
]:
    """
    Choisit (x,y,epsg) pour un groupe id_site. Si conflit, préfère EPSG connu
    + point dans bbox WGS84, sinon ligne avec `date` la plus récente.
    """
    rows: list[dict] = []
    for _, r in g.iterrows():
        rows.append(
            {
                "x": r["_xf"],
                "y": r["_yf"],
                "epsg": r["_epsg"],
                "date": r["_date_parsed"],
            }
        )

    def key(r: dict) -> tuple:
        ok_bounds = False
        x, y = r["x"], r["y"]
        xy_ok = (
            x is not None
            and y is not None
            and math.isfinite(float(x))
            and math.isfinite(float(y))
        )
        if xy_ok and r["epsg"] == 4326:
            ok_bounds = wgs84_in_upper_rhine_bounds(float(x), float(y))
        elif xy_ok and r["epsg"] == 25832:
            try:
                lon, lat = _t_25832_4326().transform(float(x), float(y))
                ok_bounds = wgs84_in_upper_rhine_bounds(lon, lat)
            except Exception:
                ok_bounds = False
        has_epsg = r["epsg"] is not None
        dt = r["date"]
        ts = -dt.timestamp() if pd.notna(dt) else 0.0
        return (0 if has_epsg else 1, 0 if ok_bounds else 1, ts)

    def row_sig(r: dict) -> tuple:
        x, y = r["x"], r["y"]
        if x is None or y is None:
            return ("missing_xy", r["epsg"])
        if not math.isfinite(float(x)) or not math.isfinite(float(y)):
            return ("missing_xy", r["epsg"])
        return (round(float(x) / COORD_TOL), round(float(y) / COORD_TOL), r["epsg"])

    signatures = {row_sig(r) for r in rows}
    conflict = len(signatures) > 1
    best = min(rows, key=key)
    details = [{"rows": rows, "chosen": best, "signatures": [str(s) for s in signatures]}]
    return best["x"], best["y"], best["epsg"], conflict, details


def _json_safe_coord_detail(detail: list[dict]) -> list[dict]:
    """Remplace Timestamp/NaT dans le détail de conflit de coordonnées."""

    def norm_row(r: dict) -> dict:
        out = dict(r)
        d = out.get("date")
        if d is not None and pd.notna(d):
            if hasattr(d, "isoformat"):
                out["date"] = d.isoformat()
            else:
                out["date"] = str(d)
        else:
            out["date"] = None
        return out

    out: list[dict] = []
    for block in detail:
        b = dict(block)
        if "rows" in b:
            b["rows"] = [norm_row(x) for x in b["rows"]]
        if "chosen" in b and isinstance(b["chosen"], dict):
            b["chosen"] = norm_row(b["chosen"])
        out.append(b)
    return out


def load_reference_points(
    sites_path: Path, golden_path: Path, variant_map: dict[str, str]
) -> list[dict]:
    refs: list[dict] = []

    if sites_path.exists():
        s = pd.read_csv(sites_path)
        s = s.drop_duplicates(subset=["site_id"], keep="first")
        for _, r in s.iterrows():
            xl, yl = r.get("x_l93"), r.get("y_l93")
            lon = lat = None
            if pd.notna(xl) and pd.notna(yl):
                try:
                    t = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
                    lon, lat = t.transform(float(xl), float(yl))
                except Exception:
                    lon, lat = None, None
            refs.append(
                {
                    "ref_id": str(r.get("site_id", "")),
                    "source_table": "sites.csv",
                    "nom_site": str(r.get("nom_site", "") or ""),
                    "commune": str(r.get("commune", "") or ""),
                    "pays": str(r.get("pays", "") or ""),
                    "lon": lon,
                    "lat": lat,
                    "commune_norm": normalize_commune(str(r.get("commune", "") or ""), variant_map),
                }
            )

    if golden_path.exists():
        g = pd.read_csv(golden_path, sep=";")
        for _, r in g.iterrows():
            lat = parse_float_cell(r.get("latitude_raw"))
            lon = parse_float_cell(r.get("longitude_raw"))
            com = str(r.get("commune", "") or "")
            refs.append(
                {
                    "ref_id": f"golden:{com}:{r.get('type_mention', '')}",
                    "source_table": "golden_sites.csv",
                    "nom_site": "",
                    "commune": com,
                    "pays": "",
                    "lon": lon,
                    "lat": lat,
                    "commune_norm": normalize_commune(com, variant_map),
                }
            )
    return refs


def main() -> None:
    periodes_cfg = load_periode_config(REF_PERIODES)
    variant_map = load_toponyme_maps(REF_TOPONYMES)
    type_patterns = load_type_alias_patterns(REF_TYPES)

    df = load_excel_sites(SOURCE_XLSX)
    row_count_raw = len(df)
    if row_count_raw != 1083:
        print(
            f"  AVERTISSEMENT: {row_count_raw} lignes lues (attendu 1083).",
            file=sys.stderr,
        )

    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"Colonnes manquantes: {missing}; présentes: {list(df.columns)}")

    # T1 — nettoyage (la colonne `date` est conservée telle quelle pour le tri d’agrégation uniquement)
    text_cols = (
        "commune",
        "lieu_dit",
        "lieu_dit_autre",
        "pays",
        "admin1",
        "ref_biblio",
        "ref_rapport",
        "commentaire",
        "decouverte_operation",
        "auteur",
    )
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].apply(strip_text)

    df["_xf"] = df["x"].apply(parse_float_cell)
    df["_yf"] = df["y"].apply(parse_float_cell)
    df["_epsg"] = df["epsg_coord"].apply(parse_epsg)
    df["_date_parsed"] = pd.to_datetime(df["date"], errors="coerce")

    epsg_missing = df[df["_epsg"].isna()].index.astype(int).tolist()
    epsg_missing_ids = df.loc[df["_epsg"].isna(), "id_site"].astype(int).tolist()

    # T2 — agrégation
    coordinate_conflicts: list[dict] = []
    agg_rows: list[dict] = []

    for sid, g in df.groupby("id_site", sort=True):
        g = g.reset_index(drop=True)
        pays = g["pays"].iloc[0]
        pays_code = PAYS_TO_CODE.get(pays, pays[:2].upper() if pays else "")
        admin1 = g["admin1"].dropna().astype(str).str.strip()
        admin1_out = admin1.iloc[0] if len(admin1) else ""
        commune = g["commune"].iloc[0]
        biblio_merged = merge_unique_texts(*g["ref_biblio"].tolist())
        rapports_merged = merge_unique_texts(*g["ref_rapport"].tolist())
        comment_merged = merge_unique_texts(*g["commentaire"].tolist(), split_seps=";")
        dec_op = g["decouverte_operation"].drop_duplicates().tolist()
        dec_op_out = " ; ".join(collapse_spaces(x) for x in dec_op if collapse_spaces(x))
        years = g["decouverte_annee"].dropna().astype(str).str.strip()
        years = [y for y in years.tolist() if y]
        dec_an_out = years[0] if len(years) == 1 else (" / ".join(dict.fromkeys(years)) if years else "")

        lieu_dit = g["lieu_dit"].iloc[0]
        lda = g["lieu_dit_autre"].iloc[0]
        if not lieu_dit and lda:
            lieu_dit = lda
        nom_site = lieu_dit or lda or commune or f"Site {sid}"

        x, y, epsg, conflict, detail = pick_coordinate_from_group(g)
        if conflict:
            coordinate_conflicts.append(
                {"id_site": int(sid), "detail": _json_safe_coord_detail(detail)}
            )

        agg_rows.append(
            {
                "id_site": int(sid),
                "pays": pays,
                "pays_code": pays_code,
                "admin1": admin1_out,
                "commune": commune,
                "lieu_dit": g["lieu_dit"].iloc[0],
                "lieu_dit_autre": g["lieu_dit_autre"].iloc[0],
                "nom_site": nom_site,
                "decouverte_annee": dec_an_out,
                "decouverte_operation": dec_op_out,
                "bibliographie": merge_unique_texts(biblio_merged, rapports_merged),
                "rapports": rapports_merged,
                "commentaire": comment_merged,
                "_x": x,
                "_y": y,
                "_epsg": epsg,
            }
        )

    agg = pd.DataFrame(agg_rows)
    site_count_aggregated = len(agg)

    # T3 + T4 — inférence texte + projection
    coordinates_suspicious: list[dict] = []
    period_inferred_ids: list[int] = []
    type_inferred_ids: list[int] = []

    out_records: list[dict] = []

    for _, r in agg.iterrows():
        blob = " ".join(
            filter(
                None,
                [
                    str(r.get("commentaire", "")),
                    str(r.get("lieu_dit", "")),
                    str(r.get("lieu_dit_autre", "")),
                    str(r.get("nom_site", "")),
                ],
            )
        )
        periode, sous, dd, df_in, p_inf = infer_period_from_text(blob, periodes_cfg)
        if p_inf:
            period_inferred_ids.append(int(r["id_site"]))
        t_site, t_inf = infer_type_site(blob, type_patterns)
        if t_inf:
            type_inferred_ids.append(int(r["id_site"]))

        lon, lat, x_l93, y_l93, susp, _proj_note = project_row(r["_x"], r["_y"], r["_epsg"])
        if susp:
            coordinates_suspicious.append(
                {
                    "id_site": int(r["id_site"]),
                    "longitude": lon,
                    "latitude": lat,
                    "epsg": r["_epsg"],
                }
            )

        inferred_any = p_inf or t_inf
        confiance = "HIGH"
        if r["_epsg"] is None or r["_x"] is None:
            confiance = "LOW"
        elif susp:
            confiance = "MEDIUM"
        if inferred_any and confiance == "HIGH":
            confiance = "MEDIUM"

        out_records.append(
            {
                "site_id": f"ALSACE-BASEL-AF-{r['id_site']}",
                "id_site_source": int(r["id_site"]),
                "nom_site": r["nom_site"],
                "commune": r["commune"],
                "lieu_dit": r["lieu_dit"],
                "pays": r["pays_code"] or r["pays"],
                "admin1": r["admin1"],
                "longitude": lon,
                "latitude": lat,
                "x_l93": x_l93,
                "y_l93": y_l93,
                "epsg_source": r["_epsg"],
                "decouverte_annee": r["decouverte_annee"],
                "decouverte_operation": r["decouverte_operation"],
                "periode": periode,
                "sous_periode": sous if sous else "",
                "datation_debut": dd,
                "datation_fin": df_in,
                "type_site": t_site,
                "confiance": confiance,
                "source": SOURCE_TAG,
                "bibliographie": r["bibliographie"],
                "rapports": r["rapports"],
                "commentaire": r["commentaire"],
                "_inferred_period": p_inf,
                "_inferred_type": t_inf,
            }
        )

    out_df = pd.DataFrame(out_records)
    cols_export = [
        "site_id",
        "id_site_source",
        "nom_site",
        "commune",
        "lieu_dit",
        "pays",
        "admin1",
        "longitude",
        "latitude",
        "x_l93",
        "y_l93",
        "epsg_source",
        "decouverte_annee",
        "decouverte_operation",
        "periode",
        "sous_periode",
        "datation_debut",
        "datation_fin",
        "type_site",
        "confiance",
        "source",
        "bibliographie",
        "rapports",
        "commentaire",
    ]
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_df[cols_export].to_csv(OUT_CLEANED, index=False, encoding="utf-8")

    # T5 — dédup
    ref_points = load_reference_points(SITES_CSV, GOLDEN_CSV, variant_map)
    duplicates_pairs: list[dict] = []

    for _, r in out_df.iterrows():
        lon, lat = r.get("longitude"), r.get("latitude")
        if lon is None or lat is None or (isinstance(lon, float) and pd.isna(lon)):
            continue
        lon, lat = float(lon), float(lat)
        com = str(r.get("commune", "") or "")
        lieu = str(r.get("lieu_dit", "") or "")
        nom = str(r.get("nom_site", "") or "")
        sid = str(r.get("site_id", ""))

        for ref in ref_points:
            if ref["lon"] is None or ref["lat"] is None:
                continue
            d_m = haversine_m(lon, lat, float(ref["lon"]), float(ref["lat"]))
            fuzzy_lieu_comm = max(
                fuzzy_token_sort_ratio(lieu, ref["commune"]),
                fuzzy_token_sort_ratio(com, ref["commune"]),
                fuzzy_token_sort_ratio(lieu, ref["nom_site"]),
                fuzzy_token_sort_ratio(com, ref["nom_site"]),
                fuzzy_token_sort_ratio(nom, ref["nom_site"]),
            )
            ok_comm = communes_compatible(com, ref["commune"], variant_map)
            nearby = d_m < DEDUP_DISTANCE_M
            # (distance < 500 m et commune compatible) OU (même emprise < 500 m et fuzzy fort)
            match_distance_commune = nearby and ok_comm
            match_fuzzy_nearby = nearby and fuzzy_lieu_comm >= FUZZY_THRESHOLD
            if match_distance_commune or match_fuzzy_nearby:
                if match_distance_commune:
                    rule = "distance_lt_500m_and_commune"
                else:
                    rule = "distance_lt_500m_and_fuzzy_ge_0.85"
                duplicates_pairs.append(
                    {
                        "alsace_basel_site_id": sid,
                        "reference_id": ref["ref_id"],
                        "reference_table": ref["source_table"],
                        "distance_m": round(d_m, 1),
                        "fuzzy_score": round(fuzzy_lieu_comm, 3),
                        "rule": rule,
                    }
                )

    report: dict[str, Any] = {
        "row_count_raw": int(row_count_raw),
        "site_count_aggregated": int(site_count_aggregated),
        "expected_row_count": 1083,
        "expected_max_sites": 1070,
        "epsg_missing": {"row_indices_excel_order": epsg_missing[:200], "id_site_values": epsg_missing_ids[:200], "count": len(epsg_missing)},
        "coordinates_suspicious": coordinates_suspicious[:300],
        "coordinate_conflicts": coordinate_conflicts,
        "period_inferred_from_text_count": len(set(period_inferred_ids)),
        "type_inferred_from_text_count": len(set(type_inferred_ids)),
        "duplicates_with_golden_or_sites_csv": duplicates_pairs[:500],
        "duplicates_count": len(duplicates_pairs),
        "notes": [
            "EPSG:4326 attendu comme lon=x, lat=y ; EPSG:25832 en mètres UTM 32N.",
            "La colonne `date` du fichier est une métadonnée de mise à jour — non utilisée pour la chronologie Fer.",
            "Lecture XLSX : calamine en premier (workbooks avec DV XML invalide), repli openpyxl.",
            "Dédup T5 : paire retenue si distance < 500 m et (communes compatibles OU fuzzy token_sort ≥ 0,85).",
        ],
        "output_csv": str(OUT_CLEANED.relative_to(REPO_ROOT)),
        "output_report": str(OUT_REPORT.relative_to(REPO_ROOT)),
    }

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Résumé console
    print("Ingestion Alsace_Basel_AF — terminée")
    print(f"  Lignes brutes: {row_count_raw} | Sites agrégés: {site_count_aggregated}")
    print(f"  EPSG manquant: {len(epsg_missing)} | Coordonnées suspectes: {len(coordinates_suspicious)}")
    print(f"  Conflits de coordonnées (agrégation): {len(coordinate_conflicts)}")
    print(f"  Paires dédup (≤500 listées dans JSON): {len(duplicates_pairs)}")
    print(f"  CSV: {OUT_CLEANED}")
    print(f"  Rapport: {OUT_REPORT}")

    if site_count_aggregated > 1070:
        print(f"  AVERTISSEMENT: {site_count_aggregated} sites > 1070 attendus", file=sys.stderr)


if __name__ == "__main__":
    main()
