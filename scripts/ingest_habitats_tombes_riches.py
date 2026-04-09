#!/usr/bin/env python3
"""
Ingestion Excel « habitats-tombes riches Alsace-Lorraine » (BaseFerRhin).
Pipeline T1–T6 : chargement, nettoyage, classification, pas de projection,
déduplication par slug vs data/output/sites.csv, append sites_cleaned (schéma aligné) + dedup_report.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_XLSX = REPO_ROOT / "RawData/GrosFichiers - Béhague/20240425_habitats-tombes riches_Als-Lor (1).xlsx"
REF_TYPES = REPO_ROOT / "data/reference/types_sites.json"
REF_PERIODES = REPO_ROOT / "data/reference/periodes.json"
REF_TOPONYMES = REPO_ROOT / "data/reference/toponymes_fr_de.json"
SITES_CSV = REPO_ROOT / "data/output/sites.csv"
OUT_CLEANED = REPO_ROOT / "data/output/sites_cleaned.csv"
OUT_DEDUP = REPO_ROOT / "data/output/dedup_report.csv"
SOURCE_FILE_NAME = "20240425_habitats-tombes riches_Als-Lor (1).xlsx"

# Colonnes alignées sur data/output/sites_cleaned.csv (multi-sources)
CLEANED_COLUMNS = [
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

PAYS_MAP = {"D": "DE", "d": "DE", "F": "FR", "f": "FR"}
DE_LAND_HINTS = (
    "bade-wurtemberg",
    "baden-württemberg",
    "rhénanie-palatinat",
    "rheinland-pfalz",
    "rp",
    "bw",
)
FR_DEPT_NUMS = {"54", "57", "67", "68"}


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
    """variant_ascii_fold -> canonical commune."""
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


def infer_pays_from_dept_land(raw: str) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    t = collapse_spaces(str(raw))
    if not t:
        return None
    tl = ascii_fold(t)
    digits = re.sub(r"\D", "", t)
    if digits in FR_DEPT_NUMS:
        return "FR"
    for hint in DE_LAND_HINTS:
        if hint in tl:
            return "DE"
    return None


def map_type_site(type_raw: str, armement: str | float) -> str:
    """Vocabulaire aligné sur sites.csv (minuscules françaises)."""
    parts = []
    if type_raw is not None and not (isinstance(type_raw, float) and pd.isna(type_raw)):
        parts.append(str(type_raw))
    if armement is not None and not (isinstance(armement, float) and pd.isna(armement)):
        parts.append(str(armement))
    blob = " ".join(parts).lower()
    if re.search(r"tumulus|tertre|hügelgrab|grabhügel", blob, re.I):
        return "tumulus"
    if any(
        x in blob
        for x in (
            "site fortifié",
            "fortifié de hauteur",
            "de hauteur",
            "oppidum",
        )
    ):
        return "oppidum"
    if any(
        x in blob
        for x in (
            "tombe princière",
            "tombe riche",
            "tombe à char",
        )
    ):
        return "nécropole"
    if "tombe" in blob:
        return "nécropole"
    return "indéterminé"


def normalize_datation_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t.strip())
    t = re.sub(r"La\s*Tène", "La Tène", t, flags=re.I)
    t = re.sub(r"\bLTA\b", "LT A", t, flags=re.I)
    t = re.sub(r"\bLTB\b", "LT B", t, flags=re.I)
    t = re.sub(r"\bLTC\b", "LT C", t, flags=re.I)
    t = re.sub(r"\bLTD\b", "LT D", t, flags=re.I)
    t = re.sub(r"LT\s*A(\d)", r"LT A\1", t, flags=re.I)
    return t


def load_periode_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_periode_datation(
    datation: str | float,
    datation_tum: str | float,
    periodes_cfg: dict,
) -> tuple[str, str | None, int | None, int | None]:
    """
    Retourne (periode, sous_periode, datation_debut, datation_fin) au format sites.csv.
    periode: Hallstatt | La Tène | indéterminé | Bronze final
    """
    periodes = periodes_cfg.get("periodes", {})
    sub_re = periodes_cfg.get("sub_period_regex", "")

    def pick_text() -> str:
        for col in (datation, datation_tum):
            if col is None or (isinstance(col, float) and pd.isna(col)):
                continue
            s = collapse_spaces(str(col))
            if s and s != "?":
                return s
        return ""

    raw = pick_text()
    if not raw or raw.strip() == "?":
        return "indéterminé", None, None, None

    text = normalize_datation_text(raw)
    tl = text.lower()

    # Bronze seul (hors vocabulaire Hallstatt/La Tène)
    has_bz = bool(re.search(r"\bbz\b|bronze\s*moyen|bronze\s*final|\bbm\b", tl))
    has_iron = bool(
        re.search(
            r"hallstatt|hallstattien|ha\s*[cd]|la\s*tène|latène|lt\s*[a-d]|\bfer\b",
            tl,
        )
    )
    if has_bz and not has_iron:
        return "Bronze final", None, None, None

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

    # Période principale — transition Ha D3 / LT A (texte mixte Hallstatt + La Tène)
    if is_trans or (is_ha and is_lt):
        periode = "Hallstatt"
        sous = "Ha D3 / LT A"
        sp = trans_cfg.get("sous_periodes", {}).get("Ha D3 / LT A", {})
        dd = sp.get("date_debut") if sp else None
        df = sp.get("date_fin") if sp else None
        return periode, sous, dd, df

    if is_lt and not is_ha:
        periode = "La Tène"
        lt_subs = lt_cfg.get("sous_periodes", {})
        if sous:
            key_match = None
            sk = sous.replace(" ", "").upper()
            for k in lt_subs:
                if sk.replace(" ", "").upper() in k.replace(" ", "").upper() or k.upper() in sous.upper():
                    key_match = k
                    break
            if key_match:
                sp = lt_subs[key_match]
                return periode, key_match, sp.get("date_debut"), sp.get("date_fin")
        return periode, sous, lt_cfg.get("date_debut"), lt_cfg.get("date_fin")

    if is_ha:
        periode = "Hallstatt"
        ha_subs = hall_cfg.get("sous_periodes", {})
        if not sous:
            mh = re.search(r"Hallstatt\s+([CD])(\d?)\b", text, re.I)
            if mh:
                g1, g2 = mh.group(1).upper(), mh.group(2)
                sous = f"Ha {g1}" + (g2 if g2 else "")
        if sous:
            norm = sous
            for k in ha_subs:
                if k.replace(" ", "").lower() in norm.replace(" ", "").lower():
                    sp = ha_subs[k]
                    return periode, k, sp.get("date_debut"), sp.get("date_fin")
        return periode, sous, hall_cfg.get("date_debut"), hall_cfg.get("date_fin")

    # Hallstatt écrit en toutes lettres sans sous-période captée
    if re.search(r"hallstatt", tl):
        return "Hallstatt", sous, hall_cfg.get("date_debut"), hall_cfg.get("date_fin")

    if has_bz and has_iron:
        return "indéterminé", sous, None, None

    return "indéterminé", sous, None, None


def make_slug(commune: str, nom_site: str, pays: str) -> str:
    return f"{ascii_fold(commune)}|{ascii_fold(nom_site)}|{str(pays).upper()}"


def new_site_id(commune: str, nom_site: str, pays: str, idx: int) -> str:
    h = hashlib.sha256(
        f"{commune}|{nom_site}|{pays}|{idx}|habitats-tombes-riches".encode()
    ).hexdigest()[:16]
    return f"SITE-{h}"


def build_armement_summary(row: pd.Series, complement_col: str) -> str:
    parts = []
    for c in ("armement", complement_col):
        if c in row.index:
            v = row[c]
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                s = collapse_spaces(str(v))
                if s:
                    parts.append(s)
    s = " ; ".join(parts)
    return (s[:500] + "…") if len(s) > 500 else s


def main() -> None:
    periodes_cfg = load_periode_config(REF_PERIODES)
    variant_map = load_toponyme_maps(REF_TOPONYMES)

    df = pd.read_excel(SOURCE_XLSX, engine="openpyxl", header=0)
    df.columns = df.columns.str.strip()
    unnamed = [c for c in df.columns if c.startswith("Unnamed")]
    complement_col = "complement_armement"
    if unnamed:
        df = df.rename(columns={unnamed[0]: complement_col})
    elif complement_col not in df.columns:
        df[complement_col] = pd.NA

    # T2 — lignes entièrement vides
    df = df.dropna(how="all")

    # Pays
    def norm_pays(row) -> str:
        p = row.get("Pays")
        if p is not None and not (isinstance(p, float) and pd.isna(p)):
            ps = str(p).strip()
            if ps in PAYS_MAP:
                return PAYS_MAP[ps]
        inf = infer_pays_from_dept_land(row.get("Dept/Land"))
        if inf:
            return inf
        return ""

    df["_pays"] = df.apply(norm_pays, axis=1)

    df["admin_raw"] = df["Dept/Land"].apply(
        lambda x: collapse_spaces(str(x)) if pd.notna(x) and str(x).strip() else pd.NA
    )

    def norm_dept_land(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return pd.NA
        s = collapse_spaces(str(x))
        digits = re.sub(r"\D", "", s)
        if digits in FR_DEPT_NUMS:
            return digits.zfill(2) if len(digits) == 1 else digits
        return s

    df["Dept/Land"] = df["Dept/Land"].apply(norm_dept_land)

    for col in ("Commune", "Lieudit"):
        df[col] = df[col].apply(
            lambda x: pd.NA
            if x is None or (isinstance(x, float) and pd.isna(x)) or not str(x).strip()
            else collapse_spaces(str(x))
        )

    df["commune_norm"] = df["Commune"].apply(lambda c: normalize_commune(c, variant_map))

    def nom_site_row(row) -> str:
        if pd.notna(row.get("Lieudit")) and str(row["Lieudit"]).strip():
            return str(row["Lieudit"])
        if pd.notna(row.get("Commune")) and str(row["Commune"]).strip():
            return str(row["Commune"])
        return "sans nom"

    df["nom_site"] = df.apply(nom_site_row, axis=1)

    df["x_l93"] = pd.NA
    df["y_l93"] = pd.NA
    df["longitude"] = pd.NA
    df["latitude"] = pd.NA

    df["type_site"] = df.apply(
        lambda r: map_type_site(r.get("type"), r.get("armement")), axis=1
    )

    parsed = df.apply(
        lambda r: parse_periode_datation(
            r.get("Datation"), r.get("Datation globale Tum"), periodes_cfg
        ),
        axis=1,
        result_type="expand",
    )
    df["periode"] = parsed[0]
    df["sous_periode"] = parsed[1]
    df["datation_debut"] = parsed[2]
    df["datation_fin"] = parsed[3]

    df["armement_summary"] = df.apply(
        lambda r: build_armement_summary(r, complement_col), axis=1
    )

    def or_summary(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        s = collapse_spaces(str(v))
        return (s[:400] + "…") if len(s) > 400 else s

    df["or_summary"] = df["or"].apply(or_summary) if "or" in df.columns else ""

    df["remarques"] = df["Remarques"].apply(
        lambda x: ""
        if x is None or (isinstance(x, float) and pd.isna(x))
        else collapse_spaces(str(x))
    )

    # Retirer lignes sans commune, sans lieudit exploitable et sans pays (lignes fantômes Excel)
    def row_is_emptyish(r) -> bool:
        no_c = pd.isna(r.get("Commune")) or not str(r.get("Commune", "")).strip()
        no_l = pd.isna(r.get("Lieudit")) or not str(r.get("Lieudit", "")).strip()
        p = r.get("_pays", "")
        no_p = not (isinstance(p, str) and p.strip())
        return no_c and no_l and no_p

    df = df[~df.apply(row_is_emptyish, axis=1)]

    # T5 — dédup vs sites.csv
    slug_to_site_ids: dict[str, list[str]] = {}
    if SITES_CSV.exists():
        ex = pd.read_csv(SITES_CSV)
        ex_u = ex.drop_duplicates(subset=["site_id"], keep="first")
        for _, r in ex_u.iterrows():
            slug = make_slug(
                str(r.get("commune", "") or ""),
                str(r.get("nom_site", "") or ""),
                str(r.get("pays", "") or ""),
            )
            if not slug.endswith("|DE") and not slug.endswith("|FR"):
                continue
            sid = str(r.get("site_id", ""))
            if not sid:
                continue
            slug_to_site_ids.setdefault(slug, []).append(sid)

    dedup_rows: list[dict] = []
    out_rows: list[dict] = []

    # Slugs internes (doublons Excel)
    seen_slugs: dict[str, int] = {}

    for i, (_, row) in enumerate(df.iterrows()):
        commune_out = row["commune_norm"] if row["commune_norm"] else row["Commune"]
        if commune_out is None or (isinstance(commune_out, float) and pd.isna(commune_out)):
            commune_out = ""
        else:
            commune_out = str(commune_out)

        nom_site = str(row["nom_site"])
        pays = row["_pays"] or ""
        pays = str(pays).upper()

        slug = make_slug(commune_out, nom_site, pays)
        site_id = new_site_id(commune_out, nom_site, pays, i)

        dup_of = ""
        needs_review = False
        status = "clean"
        notes = ""

        if slug in seen_slugs:
            needs_review = True
            status = "internal_duplicate_slug"
            notes = f"Même slug qu’une autre ligne Excel (index précédent {seen_slugs[slug]})"
        seen_slugs[slug] = i

        matches = slug_to_site_ids.get(slug, [])
        uniq = list(dict.fromkeys(matches))
        if len(uniq) == 1:
            dup_of = uniq[0]
            status = "match_existing_site"
            notes = "Correspondance exacte commune|nom_site|pays avec sites.csv"
        elif len(uniq) > 1:
            needs_review = True
            status = "ambiguous_existing"
            notes = f"Plusieurs site_id pour le même slug: {', '.join(uniq[:5])}"

        dedup_rows.append(
            {
                "excel_row_index": i,
                "new_site_id": site_id,
                "slug": slug,
                "duplicate_of_site_id": dup_of,
                "needs_review": needs_review,
                "status": status,
                "notes": notes,
            }
        )

        phase_id = f"{site_id}-PH1"
        out_rows.append(
            {
                "site_id": site_id,
                "nom_site": nom_site,
                "commune": commune_out,
                "pays": pays,
                "type_site": row["type_site"],
                "x_l93": row["x_l93"],
                "y_l93": row["y_l93"],
                "longitude": row["longitude"],
                "latitude": row["latitude"],
                "phase_id": phase_id,
                "periode": row["periode"],
                "sous_periode": row["sous_periode"] if pd.notna(row["sous_periode"]) else "",
                "datation_debut": row["datation_debut"] if pd.notna(row["datation_debut"]) else "",
                "datation_fin": row["datation_fin"] if pd.notna(row["datation_fin"]) else "",
                "sources_count": 1,
                "source_references": SOURCE_FILE_NAME,
                "occupation_necropole_raw": "",
                "chronologie_comment": "",
                "source_file": SOURCE_FILE_NAME,
                "armement_summary": row["armement_summary"],
                "or_summary": row["or_summary"],
                "remarques": row["remarques"],
            }
        )

    out_df = pd.DataFrame(out_rows, columns=CLEANED_COLUMNS)
    for _col in ("x_l93", "y_l93", "longitude", "latitude", "datation_debut", "datation_fin"):
        out_df[_col] = pd.to_numeric(out_df[_col], errors="coerce")
    out_df["sources_count"] = pd.to_numeric(out_df["sources_count"], errors="coerce").fillna(1).astype(int)

    if OUT_CLEANED.exists():
        existing = pd.read_csv(OUT_CLEANED)
        # Ré-exécution : retirer les lignes déjà produites par ce classeur
        if "source_file" in existing.columns:
            sf = existing["source_file"].fillna("").astype(str)
            existing = existing.loc[sf != SOURCE_FILE_NAME]
        for c in CLEANED_COLUMNS:
            if c not in existing.columns:
                existing[c] = pd.NA
        existing = existing[CLEANED_COLUMNS]
        for _col in ("x_l93", "y_l93", "longitude", "latitude", "datation_debut", "datation_fin"):
            if _col in existing.columns:
                existing[_col] = pd.to_numeric(existing[_col], errors="coerce")
        if "sources_count" in existing.columns:
            existing["sources_count"] = pd.to_numeric(
                existing["sources_count"], errors="coerce"
            )
        combined = pd.concat([existing, out_df], ignore_index=True)
    else:
        combined = out_df

    combined.to_csv(OUT_CLEANED, index=False, encoding="utf-8")
    pd.DataFrame(dedup_rows).to_csv(OUT_DEDUP, index=False, encoding="utf-8")

    # Résumé console
    n = len(out_df)
    n_total = len(combined)
    n_match = sum(1 for r in dedup_rows if r["status"] == "match_existing_site")
    n_amb = sum(1 for r in dedup_rows if r["status"] == "ambiguous_existing")
    n_int = sum(1 for r in dedup_rows if r["status"] == "internal_duplicate_slug")
    print(f"Export: {OUT_CLEANED} ({n} lignes ingérées ce run, {n_total} total)")
    print(f"Dedup report: {OUT_DEDUP}")
    print(f"Correspondances sites.csv (slug exact): {n_match}")
    print(f"Ambiguïtés base existante: {n_amb}")
    print(f"Doublons internes (même slug dans le classeur): {n_int}")
    print("\nRépartition type_site:")
    print(out_df["type_site"].value_counts().to_string())
    print("\nRépartition periode:")
    print(out_df["periode"].value_counts().to_string())
    missing_pays = (out_df["pays"] == "").sum()
    if missing_pays:
        print(f"\nATTENTION: {missing_pays} ligne(s) sans pays après inférence.")


if __name__ == "__main__":
    main()
