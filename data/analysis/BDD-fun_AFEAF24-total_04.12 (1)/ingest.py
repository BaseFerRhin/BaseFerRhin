#!/usr/bin/env python3
"""Pipeline d'ingestion — AFEAF 2024 base funéraire (échantillon sample_data.csv).

Le XLSX complet est absent du dépôt : seul sample_data.csv est traité.
Sorties : sepultures_long.csv, sites_cleaned.csv, quality_report.json
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2].parent
ANALYSIS_DIR = Path(__file__).resolve().parent
SAMPLE_CSV = ANALYSIS_DIR / "sample_data.csv"
REF_PERIODES = ROOT / "data" / "reference" / "periodes.json"
REF_TOPONYMES = ROOT / "data" / "reference" / "toponymes_fr_de.json"
GOLDEN_SITES = ROOT / "data" / "sources" / "golden_sites.csv"
EXISTING_SITES = ROOT / "data" / "output" / "sites_cleaned.csv"

SOURCE_STRING = "AFEAF_funeraire_2024_total_0412"

OUT_SEPULTURES = ANALYSIS_DIR / "sepultures_long.csv"
OUT_SITES = ANALYSIS_DIR / "sites_cleaned.csv"
OUT_REPORT = ANALYSIS_DIR / "quality_report.json"

# Champs oui/non/probable/indéterminé (indices après rename — rempli par détection de valeurs)
ENUM_NORMAL = {
    "oui": "oui",
    "non": "non",
    "probable": "probable",
    "indéterminé": "indéterminé",
    "indetermine": "indéterminé",
    "*": None,
    "": None,
}


def _strip_cell(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    if s == "" or s == "*":
        return None
    return s


def _norm_snippet(s: str) -> str:
    s = str(s).replace("\n", " ").strip().lower()
    s = re.sub(r"[^a-z0-9àâäéèêëïîôùûüç]+", "_", s, flags=re.IGNORECASE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "col"


def build_column_names(row0: pd.Series, row1: pd.Series) -> tuple[list[str], dict[str, str]]:
    """Fusionne les deux lignes d'en-tête en noms snake_case stables."""
    n = len(row0)
    names: list[str] = []
    counts: dict[str, int] = {}
    renamed_from_unnamed: dict[str, str] = {}

    for i in range(n):
        g0 = _strip_cell(row0.iloc[i]) or ""
        g1 = _strip_cell(row1.iloc[i]) or ""
        base_g = _norm_snippet(g0) if g0 else f"col_{i}"
        base_u = _norm_snippet(g1) if g1 else ""
        if base_u and base_u != base_g:
            base = f"{base_g}__{base_u}"
        else:
            base = base_g
        if base in counts:
            counts[base] += 1
            base = f"{base}_{counts[base]}"
        else:
            counts[base] = 0
        names.append(base)
        raw_h = str(row0.iloc[i]) if pd.notna(row0.iloc[i]) else ""
        if "unnamed" in raw_h.lower() or (isinstance(row0.index[i], str) and "unnamed" in str(row0.index[i]).lower()):
            renamed_from_unnamed[base] = f"group={g0!r} sub={g1!r}"

    return names, renamed_from_unnamed


def load_sample_two_header_rows() -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    raw = pd.read_csv(
        SAMPLE_CSV,
        sep=";",
        header=None,
        dtype=str,
        engine="python",
        keep_default_na=False,
    )
    row0, row1 = raw.iloc[0], raw.iloc[1]
    names, mapping = build_column_names(row0, row1)
    data = raw.iloc[2:].copy()
    data.columns = names
    data = data.reset_index(drop=True)
    return data, names, mapping


def clean_text_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(lambda x: _strip_cell(x))
    return out


def normalize_enum_value(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().lower()
    if s in ("*", ""):
        return None
    s = s.rstrip()
    if s in ("oui", "o", "yes"):
        return "oui"
    if s in ("non", "n", "no"):
        return "non"
    if "probable" in s:
        return "probable"
    if "indétermin" in s or "indetermin" in s:
        return "indéterminé"
    return s if s else None


def apply_enum_columns(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Normalise colonnes dont les valeurs dominantes sont oui/non/probable/indéterminé."""
    out = df.copy()
    touched = []
    skip_substr = ("genre", "sexe", "datation", "mobilier", "c14", "phase", "site", "n_st", "nmi", "individu", "dpt")
    for c in out.columns:
        cl = c.lower()
        if any(s in cl for s in skip_substr):
            continue
        ser = out[c].dropna()
        if ser.empty:
            continue
        sample = set(str(x).strip().lower() for x in ser.head(30))
        if sample <= {"oui", "non", "probable", "indéterminé", "indetermine", "*", ""} or (
            len(sample) <= 6 and any(k in sample for k in ("oui", "non", "probable", "indéterminé"))
        ):
            out[c] = out[c].map(normalize_enum_value)
            touched.append(c)
    report["t2_enum_columns_normalized"] = touched
    return out


def load_periodes() -> dict:
    with open(REF_PERIODES, encoding="utf-8") as f:
        return json.load(f)


def _normalize_chrono_text(raw: str) -> str:
    """Expose Ha D1 / LT A pour le regex quand la source écrit 'Hallstatt D1', 'La Tène B2', etc."""
    s = raw
    s = re.sub(r"Hallstatt\s*([CD])(\d?)", r"Ha \1\2", s, flags=re.IGNORECASE)
    s = re.sub(r"La\s*T[eè]ne\s*([ABCD])(\d?)", r"LT \1\2", s, flags=re.IGNORECASE)
    return s


def match_period(text: str | None, periodes_ref: dict) -> tuple[str | None, str | None, float | None, float | None, bool]:
    """Retourne (periode_affichage, sous_periode, debut, fin, mapped)."""
    if not text:
        return None, None, None, None, True
    raw = text.strip()
    if not raw or raw == "*":
        return None, None, None, None, True

    periodes = periodes_ref["periodes"]
    sub_re = re.compile(periodes_ref.get("sub_period_regex", r"(?:Ha\s*[CD](?:\d)?(?:-[CD]?\d)?|LT\s*[A-D](?:\d)?)"))
    low = raw.lower()
    norm = _normalize_chrono_text(raw)

    periode_key: str | None = None
    for pname, pdata in periodes.items():
        for pat in pdata.get("patterns_fr", []) + pdata.get("patterns_de", []):
            if pat.lower() in low:
                periode_key = pname
                break
        if periode_key:
            break

    # Toutes les correspondances regex sur le texte normalisé ; garde la sous-période la plus longue (la plus spécifique)
    sous = None
    debut, fin = None, None
    best_len = -1
    for m in sub_re.finditer(norm):
        sub_text = m.group(0)
        sub_norm = re.sub(r"\s+", " ", sub_text).strip()
        for pname, pdata in periodes.items():
            found = False
            for sp_name, sp_data in pdata.get("sous_periodes", {}).items():
                if sp_name.replace(" ", "").lower() == sub_norm.replace(" ", "").lower():
                    if len(sp_name) > best_len:
                        best_len = len(sp_name)
                        sous = sp_name
                        debut = float(sp_data["date_debut"])
                        fin = float(sp_data["date_fin"])
                        if not periode_key:
                            periode_key = pname
                    found = True
                    break
            if found:
                break

    # Phase « Hallstatt D » sans sous-phase en référentiel : intervalle Ha D1–D3 regroupé
    if not sous and re.search(r"hallstatt\s+d\b", low):
        if not re.search(r"hallstatt\s+d\s*\d", low):
            periode_key = periode_key or "HALLSTATT"
            debut = -620.0
            fin = -450.0

    affichage = None
    if periode_key == "HALLSTATT":
        affichage = "Hallstatt"
    elif periode_key == "LA_TENE":
        affichage = "La Tène"
    elif periode_key == "TRANSITION":
        affichage = "Transition"

    mapped = bool(affichage or sous)
    return affichage, sous, debut, fin, mapped


def infer_commune(libelle: str, canon_communes: list[str]) -> str | None:
    """Première commune canonique trouvée en préfixe du libellé (plus long d'abord)."""
    if not libelle:
        return None
    low = libelle.lower().strip()
    for c in sorted(canon_communes, key=len, reverse=True):
        cl = c.lower()
        if low.startswith(cl + " ") or low == cl:
            return c
    # Heuristique : premier mot-toponyme (ex. Dingsheim COS 4-1, Duttlenheim COS 1.3)
    m = re.match(r"^([A-Za-zÀ-ÿ'\-]+)", libelle.strip())
    if m:
        token = m.group(1)
        tl = token.lower()
        for c in canon_communes:
            if c.lower() == tl:
                return c
        if len(token) >= 4 and token[0].isupper():
            return token
    return None


def load_commune_list() -> list[str]:
    with open(REF_TOPONYMES, encoding="utf-8") as f:
        top = json.load(f)
    communes = []
    for row in top.get("concordance", []):
        communes.append(row["canonical"])
        communes.extend(row.get("variants", []))
    if GOLDEN_SITES.exists():
        g = pd.read_csv(GOLDEN_SITES, sep=";", dtype=str)
        communes.extend(g["commune"].dropna().unique().tolist())
    seen = set()
    out = []
    for c in communes:
        c = str(c).strip()
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


def load_golden_coords() -> dict[str, tuple[float, float]]:
    if not GOLDEN_SITES.exists():
        return {}
    g = pd.read_csv(GOLDEN_SITES, sep=";", dtype=str)
    d: dict[str, tuple[float, float]] = {}
    for _, r in g.iterrows():
        com = str(r.get("commune", "")).strip()
        if not com:
            continue
        try:
            lat = float(str(r["latitude_raw"]).replace(",", "."))
            lon = float(str(r["longitude_raw"]).replace(",", "."))
        except (ValueError, KeyError):
            continue
        d.setdefault(com.lower(), (lat, lon))
    return d


def site_key(dpt: str | None, libelle: str | None) -> str:
    a = (dpt or "").strip()
    b = re.sub(r"\s+", " ", (libelle or "").strip().lower())
    h = hashlib.sha256(f"{a}|{b}".encode("utf-8")).hexdigest()[:16]
    return h


def site_id_from_key(key: str) -> str:
    return f"SITE-{key}"


def classify_site_type(row: pd.Series, col_names: list[str]) -> str:
    """nécropole par défaut ; tumulus seulement si la colonne « monument tumulus avéré » est oui/probable."""
    col = next(
        (c for c in col_names if "monument_tumulus" in c.lower() or "tumulus_av" in c.lower()),
        None,
    )
    if not col:
        return "nécropole"
    # ex. monument_tumulus_avéré__tumulus — exclure n°, diamètre, nombre dans le tumulus
    if "n_tumulus" in col or "diametre_tumulus" in col or "nombre_de_sep_dans_le_tumulus" in col:
        return "nécropole"
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "nécropole"
    vs = str(v).strip().lower()
    if vs in ("oui", "probable"):
        return "tumulus"
    return "nécropole"


def wgs84_to_l93(lon: float, lat: float) -> tuple[float | None, float | None]:
    try:
        from pyproj import Transformer

        t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
        x, y = t.transform(lon, lat)
        return round(x, 2), round(y, 2)
    except Exception:
        return None, None


def aggregate_armement_or(row: pd.Series, cols: list[str]) -> tuple[str, str]:
    arm_parts, or_parts = [], []
    for c in cols:
        cl = c.lower()
        if cl.endswith("__armement") or (cl.endswith("_armement") and "armes_dépos" not in cl):
            v = row.get(c)
            if v and str(v).lower() not in ("non", "indéterminé", ""):
                arm_parts.append(str(v))
        if cl.endswith("__parure") or cl.endswith("_parure"):
            v = row.get(c)
            if v and str(v).lower() not in ("non", "indéterminé", ""):
                or_parts.append(str(v))
    return "; ".join(dict.fromkeys(arm_parts))[:500], "; ".join(dict.fromkeys(or_parts))[:500]


def run() -> None:
    report: dict = {
        "source": SOURCE_STRING,
        "input_file": str(SAMPLE_CSV.relative_to(ROOT)),
        "note_echantillon": "Traitement limité à sample_data.csv (~35 lignes fichier / 19 lignes données). Le fichier XLSX complet (401 lignes) est absent du dépôt.",
        "row_count_raw_file_lines_approx": None,
    }

    df, col_names, unnamed_map = load_sample_two_header_rows()
    report["row_count_raw_logical_rows"] = len(df) + 2
    report["data_rows_after_header_fix"] = len(df)
    report["columns_renamed_from_unnamed"] = unnamed_map
    report["column_names_final"] = col_names

    df = clean_text_df(df)
    df = apply_enum_columns(df, report)

    # Colonnes clés
    def first_col(*subs: str) -> str | None:
        for c in col_names:
            for s in subs:
                if s.lower() in c.lower():
                    return c
        return None

    c_dpt = col_names[0] if col_names else None
    c_site = col_names[1] if len(col_names) > 1 else None
    c_nst = col_names[2] if len(col_names) > 2 else None
    c_dat = first_col("datation_mob", "datation__datation")
    if c_dat is None:
        for c in col_names:
            if "datation" in c.lower() and "c14" not in c.lower():
                c_dat = c
                break
    c_nmi = None
    for c in col_names:
        if c.endswith("__nmi") or (c == "nmi" or "__nmi" in c):
            c_nmi = c
            break
    if c_nmi is None:
        for c in col_names:
            if "nmi" in c.lower() and "type" not in c.lower():
                c_nmi = c
                break
    c_genre = next((c for c in col_names if "genre" in c.lower() and "mobilier" in c.lower()), None)

    periodes_ref = load_periodes()
    communes = load_commune_list()
    golden_ll = load_golden_coords()

    period_unmapped: list[dict] = []
    commune_failures: list[dict] = []
    duplicates_golden: list[dict] = []
    golden_df = pd.read_csv(GOLDEN_SITES, sep=";", dtype=str) if GOLDEN_SITES.exists() else None

    df["site_key"] = [site_key(df.iloc[i][c_dpt], df.iloc[i][c_site]) for i in range(len(df))]
    df["numero_structure"] = df[c_nst] if c_nst else None

    # Période par ligne
    periode_rows = []
    conf_rows = []
    for i, r in df.iterrows():
        texts = []
        if c_dat and r.get(c_dat):
            texts.append(str(r[c_dat]))
        if c_genre and r.get(c_genre):
            texts.append(str(r[c_genre]))
        # phase chrono / c14
        for c in col_names:
            if "phase_chrono" in c or "c14" in c.lower():
                if r.get(c):
                    texts.append(str(r[c]))
        joined = " | ".join(texts)
        aff, sous, db, de, mapped = match_period(joined, periodes_ref)
        if joined and not aff and not sous:
            period_unmapped.append({"row": int(i), "text": joined[:200]})
        periode_rows.append((aff, sous, db, de))
        conf_rows.append("MEDIUM" if aff or sous else "LOW")

    df["_periode"] = [p[0] for p in periode_rows]
    df["_sous_periode"] = [p[1] for p in periode_rows]
    df["_ddb"] = [p[2] for p in periode_rows]
    df["_dde"] = [p[3] for p in periode_rows]
    df["_confiance"] = conf_rows

    # Commune
    communes_infer = []
    for i, r in df.iterrows():
        lab = r.get(c_site) if c_site else None
        com = infer_commune(lab or "", communes) if lab else None
        if lab and not com:
            commune_failures.append({"row": int(i), "libelle": lab})
        communes_infer.append(com)

    df["_commune"] = communes_infer

    # Type site par ligne
    df["_type_site"] = [classify_site_type(df.iloc[i], col_names) for i in range(len(df))]

    # Références existantes pour dédup
    existing_keys = set()
    existing_labels = []
    if EXISTING_SITES.exists():
        ex = pd.read_csv(EXISTING_SITES, dtype=str)
        for _, r in ex.iterrows():
            existing_labels.append((str(r.get("commune", "")), str(r.get("nom_site", ""))))
    for i, r in df.iterrows():
        com = r.get("_commune") or ""
        nom = r.get(c_site) or ""
        for ec, en in existing_labels:
            if ec and com and ec.lower() == com.lower() and nom and en and en.lower() in nom.lower():
                duplicates_golden.append(
                    {"row": int(i), "match": "sites_cleaned", "commune": com, "nom_site": nom}
                )
                break
        if golden_df is not None:
            for _, gr in golden_df.iterrows():
                rt = str(gr.get("raw_text", ""))
                if com and com.lower() in rt.lower() and nom and str(nom).split()[0].lower() in rt.lower():
                    duplicates_golden.append(
                        {"row": int(i), "match": "golden_sites", "commune": com, "nom_site": nom}
                    )
                    break

    seen_dup: set[tuple] = set()
    deduped: list[dict] = []
    for d in duplicates_golden:
        k = (d["row"], d["match"])
        if k not in seen_dup:
            seen_dup.add(k)
            deduped.append(d)
    duplicates_golden = deduped

    report["period_unmapped"] = period_unmapped
    report["commune_parse_failures"] = commune_failures
    report["duplicates_with_golden_or_sites_csv"] = duplicates_golden
    report["site_key_rule"] = "sha256(utf8(DPT.strip() + '|' + normalize_spaces(lower(libelle_site)))) hex digest, 16 premiers caractères"

    # Règle NMI : somme des valeurs numériques NMI par site (chaque ligne = une fiche ; NMI = effectif dépôt sur la ligne)
    report["aggregation_rule_nmi"] = (
        "Par site_key : nmi_agrege = somme des entiers parsés sur la colonne NMI "
        "(valeurs non numériques ignorées). En cas d’absence de NMI numérique sur une ligne, "
        "cette ligne compte pour 1 dans nmi_structures (nombre de fiches). "
        "Documenté pour éviter la double comptage inter-sites, pas entre lignes du même site."
    )

    def parse_nmi(v) -> int | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = str(v).strip()
        if s.isdigit():
            return int(s)
        return None

    # Export long
    long_out = df.copy()
    long_out.to_csv(OUT_SEPULTURES, index=False, encoding="utf-8")

    # Agrégation site
    site_rows = []
    for sk, g in df.groupby("site_key", sort=False):
        r0 = g.iloc[0]
        dpt = r0.get(c_dpt)
        nom = r0.get(c_site)
        com = None
        for x in g["_commune"]:
            if x:
                com = x
                break
        nmis = [parse_nmi(r.get(c_nmi)) for _, r in g.iterrows() if c_nmi]
        nmis_num = [n for n in nmis if n is not None]
        nmi_sum = sum(nmis_num) if nmis_num else len(g)
        n_struct = len(g)

        # Période site : priorité aux lignes MEDIUM
        best_i = None
        for idx, rr in g.iterrows():
            if rr.get("_confiance") == "MEDIUM":
                best_i = idx
                break
        if best_i is None:
            best_i = g.index[0]
        rr = g.loc[best_i]
        per = rr.get("_periode")
        sous = rr.get("_sous_periode")
        db, de = rr.get("_ddb"), rr.get("_dde")

        # Consensus type : tumulus si une ligne tumulus
        typ = "tumulus" if (g["_type_site"] == "tumulus").any() else "nécropole"

        lat = lon = None
        xl93 = yl93 = None
        if com:
            ll = golden_ll.get(com.lower())
            if ll:
                lat, lon = ll[0], ll[1]
                xl93, yl93 = wgs84_to_l93(lon, lat)

        arm_s, or_s = [], []
        for _, r in g.iterrows():
            a, o = aggregate_armement_or(r, col_names)
            if a:
                arm_s.append(a)
            if o:
                or_s.append(o)

        rem_parts = []
        if dpt:
            rem_parts.append(f"Dép. {dpt}")
        rg_col = [c for c in col_names if "remarque" in c.lower() and "gener" in c.lower()]
        obs_col = [c for c in col_names if "observation" in c.lower()]
        for c in rg_col + obs_col:
            for _, r in g.iterrows():
                if r.get(c):
                    rem_parts.append(str(r[c])[:200])

        resume = f"n_struct={n_struct}; NMIΣ={nmi_sum}; {typ}"
        conf_site = "MEDIUM" if per or sous else "LOW"

        site_rows.append(
            {
                "site_id": site_id_from_key(sk),
                "nom_site": nom,
                "commune": com or "",
                "pays": "FR",
                "type_site": typ,
                "x_l93": xl93 if xl93 is not None else "",
                "y_l93": yl93 if yl93 is not None else "",
                "longitude": lon if lon is not None else "",
                "latitude": lat if lat is not None else "",
                "periode": per or "",
                "sous_periode": sous or "",
                "datation_debut": db if db is not None else "",
                "datation_fin": de if de is not None else "",
                "source_file": SOURCE_STRING,
                "armement_summary": " | ".join(dict.fromkeys(arm_s))[:500],
                "or_summary": " | ".join(dict.fromkeys(or_s))[:500],
                "remarques": f"[confiance={conf_site}; {resume}] " + " | ".join(rem_parts)[:1500],
            }
        )

    sites_df = pd.DataFrame(site_rows)
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
        "periode",
        "sous_periode",
        "datation_debut",
        "datation_fin",
        "source_file",
        "armement_summary",
        "or_summary",
        "remarques",
    ]
    sites_df = sites_df.reindex(columns=cols_order)
    sites_df.to_csv(OUT_SITES, index=False, encoding="utf-8")

    report["sites_exported"] = len(sites_df)
    report["sepultures_exported"] = len(long_out)
    report["distribution_type_site"] = sites_df["type_site"].value_counts().to_dict()
    report["distribution_periode"] = sites_df["periode"].value_counts().to_dict()
    report["coords_filled"] = int((sites_df["latitude"] != "").sum())
    report["t6_outputs"] = {
        "sepultures_long": str(OUT_SEPULTURES.relative_to(ROOT)),
        "sites_cleaned": str(OUT_SITES.relative_to(ROOT)),
        "quality_report": str(OUT_REPORT.relative_to(ROOT)),
    }

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"OK — {len(long_out)} sépultures, {len(sites_df)} sites → {OUT_SITES}")


if __name__ == "__main__":
    run()
