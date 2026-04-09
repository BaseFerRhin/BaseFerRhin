#!/usr/bin/env python3
"""Analyze ALL input files from data/input/ and generate metadata + sample data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "input"
ANALYSIS_DIR = ROOT / "data" / "analysis"

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".ods", ".dbf"}


def load_file(path: Path) -> pd.DataFrame | None:
    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            return pd.read_csv(path, sep=";", encoding="utf-8", on_bad_lines="warn")
        elif ext == ".xlsx":
            for engine in ("calamine", "openpyxl"):
                try:
                    return pd.read_excel(path, engine=engine)
                except Exception:
                    continue
            return None
        elif ext == ".ods":
            return pd.read_excel(path, engine="odf")
        elif ext == ".dbf":
            from dbfread import DBF
            table = DBF(str(path), encoding="latin-1")
            return pd.DataFrame(iter(table))
    except Exception as e:
        print(f"  [ERROR] Impossible de charger {path.name}: {e}")
        return None
    return None


def parse_arkeogis_date(val: str) -> tuple[int | None, int | None]:
    m = re.match(r"(-?\d+):(-?\d+)", str(val))
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def detect_issues(df: pd.DataFrame, file_name: str) -> list[str]:
    issues: list[str] = []

    for col in df.columns:
        bad_quotes = df[col].astype(str).str.contains(r'""', na=False).sum()
        if bad_quotes > 0:
            issues.append(f"Colonne '{col}': {bad_quotes} valeurs avec guillemets doubles malformés")

    lat_col = next((c for c in df.columns if c.upper() in ("LATITUDE", "Y", "Y(L93)", "COORDONNÉES Y (LAMBERT 93)")), None)
    lon_col = next((c for c in df.columns if c.upper() in ("LONGITUDE", "X", "X(L93)", "COORDONNÉES X (LAMBERT 93)")), None)

    if lat_col and lon_col:
        lat = pd.to_numeric(df[lat_col], errors="coerce")
        lon = pd.to_numeric(df[lon_col], errors="coerce")
        zero_coords = ((lat == 0) | (lon == 0)).sum()
        if zero_coords > 0:
            issues.append(f"{zero_coords} lignes avec coordonnées à 0")

    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    if unnamed:
        issues.append(f"{len(unnamed)} colonnes sans nom (Unnamed)")

    empty_cols = [c for c in df.columns if df[c].isnull().all()]
    if empty_cols:
        issues.append(f"{len(empty_cols)} colonnes entièrement vides: {empty_cols[:5]}")

    return issues


def profile_column(series: pd.Series) -> dict:
    sample_vals = []
    for v in series.dropna().unique()[:3]:
        s = str(v)
        if len(s) > 100:
            s = s[:100] + "..."
        sample_vals.append(s)

    return {
        "name": str(series.name),
        "dtype": str(series.dtype),
        "null_count": int(series.isnull().sum()),
        "null_pct": round(series.isnull().mean() * 100, 1),
        "unique_count": int(series.nunique()),
        "sample_values": sample_vals,
    }


def detect_format_info(path: Path) -> dict:
    ext = path.suffix.lower()
    info = {"format": ext.upper().lstrip("."), "file_size_kb": path.stat().st_size // 1024}
    if ext == ".csv":
        info["separator"] = ";"
        info["encoding"] = "UTF-8"
    elif ext == ".xlsx":
        info["engine"] = "openpyxl/calamine"
    elif ext == ".ods":
        info["engine"] = "odf"
    elif ext == ".dbf":
        info["encoding"] = "latin-1"
    return info


def detect_geo_columns(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    col_names_lower = {str(c).lower(): c for c in df.columns}

    lat_candidates = ["latitude", "y", "y(l93)", "coordonnées y (lambert 93)"]
    lon_candidates = ["longitude", "x", "x(l93)", "coordonnées x (lambert 93)"]
    epsg_candidates = ["projection_system", "epsg_coord", "epsg"]

    lat_col = next((col_names_lower[k] for k in lat_candidates if k in col_names_lower), None)
    lon_col = next((col_names_lower[k] for k in lon_candidates if k in col_names_lower), None)
    epsg_col = next((col_names_lower[k] for k in epsg_candidates if k in col_names_lower), None)

    return lat_col, lon_col, epsg_col


def build_geographic(df: pd.DataFrame) -> dict:
    lat_col, lon_col, epsg_col = detect_geo_columns(df)
    geo: dict = {}

    if lat_col and lon_col:
        lat = pd.to_numeric(df[lat_col], errors="coerce").dropna()
        lon = pd.to_numeric(df[lon_col], errors="coerce").dropna()

        if len(lat) > 0 and len(lon) > 0:
            geo["lat_column"] = lat_col
            geo["lon_column"] = lon_col
            geo["min_lat"] = round(float(lat.min()), 6)
            geo["max_lat"] = round(float(lat.max()), 6)
            geo["min_lon"] = round(float(lon.min()), 6)
            geo["max_lon"] = round(float(lon.max()), 6)

            if lat.max() > 200:
                geo["projection_guess"] = "Lambert-93 (EPSG:2154)"
            else:
                geo["projection_guess"] = "WGS84 (EPSG:4326)"

    if epsg_col and epsg_col in df.columns:
        geo["epsg_column"] = epsg_col
        geo["epsg_values"] = df[epsg_col].dropna().unique().tolist()[:5]

    centroid_col = next((c for c in df.columns if str(c).upper() == "CITY_CENTROID"), None)
    if centroid_col:
        centroid_count = (df[centroid_col] == "Oui").sum()
        geo["city_centroid_pct"] = round(centroid_count / len(df) * 100, 1)

    return geo


def build_chronology(df: pd.DataFrame) -> dict:
    chrono: dict = {}

    period_col = next((c for c in df.columns if str(c).upper() == "STARTING_PERIOD"), None)
    if period_col:
        chrono["date_format"] = "ArkeoGIS (-YYYY:-YYYY)"
        all_starts = []
        for val in df[period_col]:
            s, _ = parse_arkeogis_date(str(val))
            if s is not None:
                all_starts.append(s)
        if all_starts:
            chrono["earliest"] = min(all_starts)

        end_col = next((c for c in df.columns if str(c).upper() == "ENDING_PERIOD"), None)
        if end_col:
            all_ends = []
            for val in df[end_col]:
                _, e = parse_arkeogis_date(str(val))
                if e is not None:
                    all_ends.append(e)
            if all_ends:
                chrono["latest"] = max(all_ends)

        indet = (df[period_col].astype(str).str.lower() == "indéterminé").sum()
        chrono["indeterminate_rows"] = int(indet)
        chrono["indeterminate_pct"] = round(indet / len(df) * 100, 1)

    period_keywords = ["période", "periode", "datation", "chronologie", "date"]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in period_keywords) and str(col).upper() != "STARTING_PERIOD":
            vals = df[col].dropna().unique()[:10]
            chrono[f"period_column_{col}"] = [str(v) for v in vals]

    return chrono


def build_quality(df: pd.DataFrame, issues: list[str]) -> dict:
    total = len(df)
    fill_rates = {}
    for col in df.columns:
        rate = round((1 - df[col].isnull().mean()) * 100, 1)
        fill_rates[str(col)] = rate

    avg_fill = sum(fill_rates.values()) / len(fill_rates) if fill_rates else 0
    critical_issues = [i for i in issues if "coordonnées à 0" in i or "hors zone" in i]

    if avg_fill > 80 and not critical_issues:
        confidence = "HIGH"
    elif avg_fill >= 50:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "avg_fill_rate_pct": round(avg_fill, 1),
        "lowest_fill_columns": sorted(fill_rates.items(), key=lambda x: x[1])[:5],
        "issues": issues,
        "confidence_level": confidence,
    }


def build_data_model(df: pd.DataFrame) -> dict:
    id_candidates = ["SITE_AKG_ID", "id_site", "id", "EA", "Code_national_de_l_EA", "EA_NATCODE"]
    id_col = next((c for c in id_candidates if c in df.columns), None)

    if not id_col:
        return {"grain": "Non déterminé — aucune colonne ID candidate trouvée",
                "total_rows": len(df)}

    site_counts = df[id_col].value_counts()
    return {
        "grain": f"Clé candidate: {id_col}",
        "id_column": id_col,
        "unique_count": int(site_counts.shape[0]),
        "rows_per_id_avg": round(float(site_counts.mean()), 2),
        "rows_per_id_max": int(site_counts.max()),
        "total_rows": len(df),
    }


def guess_source_context(file_name: str, df: pd.DataFrame) -> dict:
    ctx: dict = {"file_name": file_name}

    date_match = re.match(r"(\d{4})(\d{2})(\d{2})", file_name)
    if date_match:
        ctx["export_date"] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

    if "DATABASE_NAME" in df.columns and len(df) > 0:
        ctx["platform"] = "ArkeoGIS"
        ctx["database_name"] = str(df["DATABASE_NAME"].iloc[0])
    elif "Patriarche" in file_name:
        ctx["platform"] = "Patriarche (base nationale EA)"
    elif "AFEAF" in file_name or "afeaf" in file_name:
        ctx["platform"] = "AFEAF (Association Française pour l'Étude de l'Âge du Fer)"
    elif "cag_68" in file_name:
        ctx["platform"] = "Carte Archéologique de la Gaule — Haut-Rhin (68)"
    elif "ea_fr" in file_name:
        ctx["platform"] = "Entités Archéologiques (base nationale France)"
    elif "Proto_Alsace" in file_name:
        ctx["platform"] = "Base de données Protohistoire Alsace"
    elif "Alsace_Basel" in file_name:
        ctx["platform"] = "Base Alsace–Bâle âge du Fer"
    else:
        ctx["platform"] = "Inconnu"

    return ctx


def analyze_file(path: Path) -> bool:
    stem = path.stem
    out_dir = ANALYSIS_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyse de {path.name}...")
    df = load_file(path)
    if df is None:
        print(f"  [SKIP] Impossible de charger {path.name}")
        return False

    issues = detect_issues(df, path.name)

    metadata = {
        "file_name": path.name,
        "file_path": str(path.relative_to(ROOT)),
        **detect_format_info(path),
        "header_row": True,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": [profile_column(df[col]) for col in df.columns],
        "source": guess_source_context(path.name, df),
        "geographic": build_geographic(df),
        "chronology": build_chronology(df),
        "quality": build_quality(df, issues),
        "data_model": build_data_model(df),
    }

    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    sample_ext = ".csv"
    df.head(20).to_csv(out_dir / f"sample_data{sample_ext}", sep=";", index=False)

    dm = metadata["data_model"]
    unique_info = f"{dm.get('unique_count', '?')} uniques" if "unique_count" in dm else f"{dm['total_rows']} rows"
    geo = metadata["geographic"]
    geo_info = f"lat {geo.get('min_lat','?')}–{geo.get('max_lat','?')}" if "min_lat" in geo else "pas de coordonnées"

    print(f"  [OK] {path.suffix.upper()} | {len(df)} rows x {len(df.columns)} cols | {unique_info}")
    print(f"       Geo: {geo_info} | Qualité: {metadata['quality']['confidence_level']} ({len(issues)} issues)")
    return True


def main() -> None:
    all_files = sorted(
        f for f in INPUT_DIR.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith(".")
    )

    doc_files = sorted(
        f for f in INPUT_DIR.iterdir()
        if f.suffix.lower() == ".doc" and not f.name.startswith(".")
    )

    print(f"Fichiers supportés (CSV/XLSX/ODS/DBF): {len(all_files)}")
    print(f"Fichiers Word (.doc legacy, non parsable): {len(doc_files)}")
    print()

    success = 0
    for path in all_files:
        if analyze_file(path):
            success += 1
        print()

    for doc in doc_files:
        stem = doc.stem
        out_dir = ANALYSIS_DIR / stem
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "file_name": doc.name,
            "file_path": str(doc.relative_to(ROOT)),
            "format": "DOC",
            "file_size_kb": doc.stat().st_size // 1024,
            "note": "Format Word .doc legacy — nécessite antiword ou LibreOffice pour extraction texte",
            "source": guess_source_context(doc.name, pd.DataFrame()),
            "quality": {"confidence_level": "LOW", "issues": ["Format .doc legacy non parsable directement"]},
        }
        (out_dir / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  [DOC] {doc.name} ({meta['file_size_kb']}KB) — metadata stub créé")

    print(f"\nTerminé: {success}/{len(all_files)} fichiers data analysés + {len(doc_files)} fichiers DOC référencés")


if __name__ == "__main__":
    main()
