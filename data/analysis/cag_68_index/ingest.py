#!/usr/bin/env python3
"""Ingestion CAG 68 index : résolution communes, enrichissements, export CSV + rapport."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

INDEX_JSON = SCRIPT_DIR / "index_entries.json"
COMMUNES_JSON = REPO_ROOT / "data/analysis/cag_68_texte/communes.json"
PERIODES_JSON = REPO_ROOT / "data/reference/periodes.json"
TYPES_JSON = REPO_ROOT / "data/reference/types_sites.json"
TOPONYMES_JSON = REPO_ROOT / "data/reference/toponymes_fr_de.json"

OUT_CSV = SCRIPT_DIR / "index_entries.csv"
OUT_REPORT = SCRIPT_DIR / "quality_report.json"

# Signaux forts protohistoriques (HABITAT exclu : alias « fosse », « fossé », etc. trop génériques seuls)
_STRONG_IRON_TYPES = frozenset(
    {"OPPIDUM", "NECROPOLE", "TUMULUS", "DEPOT", "SANCTUAIRE", "ATELIER"}
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def categorize_terme(terme: str) -> str:
    t = terme.lower()
    mobilier_kw = [
        "fibule", "bracelet", "anneau", "épée", "lance", "céramique",
        "amphore", "vase", "perle", "monnaie", "hache", "couteau",
        "agrafe", "arme", "applique", "boucle", "clou", "aiguille",
    ]
    structure_kw = [
        "mur", "four", "fossé", "silo", "cave", "fosse", "puits",
        "fondation", "sol", "aire", "enclos", "palissade",
    ]
    period_kw = [
        "hallstatt", "tène", "bronze", "néolith", "romain", "méroving",
        "médiéval", "antiq",
    ]
    material_kw = [
        "bronze", "fer", "or", "argent", "verre", "os", "silex",
        "lignite", "ambre", "argile",
    ]
    funerary_kw = [
        "tombe", "tumulus", "nécropole", "sépulture", "inhumation",
        "crémation", "urne", "sarcophage", "squelette",
    ]
    road_kw = ["voie", "route", "chemin", "pont", "aqueduc", "borne"]

    if any(kw in t for kw in funerary_kw):
        return "funéraire"
    if any(kw in t for kw in mobilier_kw):
        return "mobilier"
    if any(kw in t for kw in structure_kw):
        return "structure"
    if any(kw in t for kw in period_kw):
        return "période"
    if any(kw in t for kw in material_kw):
        return "matériau"
    if any(kw in t for kw in road_kw):
        return "voirie"
    return "autre"


def build_commune_index(
    communes: list[dict],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """numero -> nom ; numero -> periodes_mentionnees."""
    by_num: dict[str, str] = {}
    periods_by_num: dict[str, list[str]] = {}
    for c in communes:
        n = str(c.get("numero", "")).zfill(3)
        by_num[n] = c.get("nom", "")
        periods_by_num[n] = list(c.get("periodes_mentionnees") or [])
    return by_num, periods_by_num


def build_period_patterns(periodes_data: dict) -> list[tuple[str, str]]:
    """Liste (pattern, clé) triée par longueur décroissante."""
    out: list[tuple[str, str]] = []
    periodes = periodes_data.get("periodes") or {}
    for key, block in periodes.items():
        for p in block.get("patterns_fr") or []:
            out.append((p, key))
        for p in block.get("patterns_de") or []:
            out.append((p, key))
    # Lemmes d'index du type « Tène (La) » : « La Tène » n'est pas une sous-chaîne
    out.extend(
        [
            ("Tène", "LA_TENE"),
            ("tene", "LA_TENE"),
            ("Hallstatt", "HALLSTATT"),
            ("hallstatt", "HALLSTATT"),
        ]
    )
    out.sort(key=lambda x: len(x[0]), reverse=True)
    return out


def match_periods(
    text: str,
    patterns: list[tuple[str, str]],
) -> list[str]:
    if not text:
        return []
    t = text
    found: list[str] = []
    seen: set[str] = set()
    for pat, key in patterns:
        if pat in t and key not in seen:
            found.append(key)
            seen.add(key)
    return found


def build_toponyme_index(topo_data: dict) -> list[tuple[str, str]]:
    """(needle_lower, canonical) longest first."""
    rows: list[tuple[str, str]] = []
    for item in topo_data.get("concordance") or []:
        can = item.get("canonical") or ""
        variants = [can] + list(item.get("variants") or [])
        for v in variants:
            if v and v.strip():
                rows.append((v.strip().lower(), can))
    rows.sort(key=lambda x: len(x[0]), reverse=True)
    return rows


def match_toponyme(terme: str, index: list[tuple[str, str]]) -> str:
    tl = terme.lower()
    for needle, canonical in index:
        if needle in tl:
            return canonical
    return ""


def build_type_aliases(types_data: dict) -> list[tuple[str, str]]:
    """(alias_lower, type_code) longest first."""
    pairs: list[tuple[str, str]] = []
    aliases = types_data.get("aliases") or {}
    for code, langs in aliases.items():
        for lang in ("fr", "de"):
            for a in langs.get(lang) or []:
                if a:
                    pairs.append((a.lower(), code))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def _alias_in_terme(terme_lower: str, alias: str) -> bool:
    if len(alias) <= 2:
        return False
    if " " in alias or "-" in alias or "'" in alias:
        return alias in terme_lower
    return bool(re.search(r"\b" + re.escape(alias) + r"\b", terme_lower))


def match_types(terme: str, pairs: list[tuple[str, str]]) -> list[str]:
    tl = terme.lower()
    out: list[str] = []
    seen: set[str] = set()
    for alias, code in pairs:
        if code in seen:
            continue
        if _alias_in_terme(tl, alias):
            out.append(code)
            seen.add(code)
    return out


def commune_has_iron_period(periodes_commune: list[str]) -> bool:
    blob = " ".join(periodes_commune).lower()
    return "hallstatt" in blob or "tène" in blob or "tene" in blob


def iron_age_pertinent(
    periode_match: list[str],
    type_match: list[str],
    commune_iron: bool,
) -> bool:
    """Période (terme + cross_refs), commune Hallstatt/La Tène sur un renvoi, ou types forts."""
    if periode_match:
        return True
    if commune_iron:
        return True
    return any(x in _STRONG_IRON_TYPES for x in type_match)


def iron_age_lexical_only(
    periode_match: list[str],
    type_match: list[str],
) -> bool:
    """Même logique sans le seul critère communal (pour cibler le lemme d'index)."""
    if periode_match:
        return True
    return any(x in _STRONG_IRON_TYPES for x in type_match)


def confidence_for_row(
    communes_ref: list[str],
    resolved_mask: list[bool],
) -> str:
    if not communes_ref:
        return "MEDIUM"
    n = len(communes_ref)
    unresolved = sum(1 for r in resolved_mask if not r)
    if unresolved == 0:
        return "HIGH"
    if unresolved <= max(1, n // 10):
        return "MEDIUM"
    return "LOW"


def main() -> None:
    entries = _load_json(INDEX_JSON)
    communes = _load_json(COMMUNES_JSON)
    periodes_data = _load_json(PERIODES_JSON)
    types_data = _load_json(TYPES_JSON)
    topo_data = _load_json(TOPONYMES_JSON)

    by_num, periods_by_num = build_commune_index(communes)
    period_patterns = build_period_patterns(periodes_data)
    topo_index = build_toponyme_index(topo_data)
    type_pairs = build_type_aliases(types_data)

    rows_out: list[dict[str, Any]] = []
    unresolved_codes: dict[str, int] = {}
    total_ref_slots = 0
    resolved_ref_slots = 0

    for e in entries:
        terme = e["terme"]
        communes_ref = [str(x).zfill(3) for x in e["communes_ref"]]
        cross_list = e.get("cross_refs") or []
        cross_text = "; ".join(cross_list) if cross_list else ""

        noms: list[str] = []
        resolved_mask: list[bool] = []
        commune_iron = False
        for code in communes_ref:
            total_ref_slots += 1
            if code in by_num:
                resolved_mask.append(True)
                resolved_ref_slots += 1
                nom = by_num[code]
                noms.append(nom)
                if commune_has_iron_period(periods_by_num.get(code, [])):
                    commune_iron = True
            else:
                resolved_mask.append(False)
                noms.append("")
                unresolved_codes[code] = unresolved_codes.get(code, 0) + 1

        periode_term = match_periods(terme, period_patterns)
        periode_cross = match_periods(cross_text, period_patterns)
        periode_keys: list[str] = []
        seen_p: set[str] = set()
        for k in periode_term + periode_cross:
            if k not in seen_p:
                periode_keys.append(k)
                seen_p.add(k)

        type_match = match_types(terme, type_pairs)
        toponyme = match_toponyme(terme, topo_index)
        cat = categorize_terme(terme)
        conf = confidence_for_row(communes_ref, resolved_mask)

        pertinent = iron_age_pertinent(periode_keys, type_match, commune_iron)
        lexical = iron_age_lexical_only(periode_keys, type_match)
        any_unresolved = any(not m for m in resolved_mask)

        rows_out.append(
            {
                "terme": terme,
                "communes_ref": ";".join(communes_ref),
                "communes_noms": ";".join(noms),
                "nb_refs": e["nb_refs"],
                "cross_refs": cross_text,
                "categorie": cat,
                "toponyme_match": toponyme,
                "periode_match": ";".join(periode_keys),
                "type_site_match": ";".join(type_match),
                "confidence": conf,
                "pertinent_age_fer": pertinent,
                "pertinent_age_fer_lexical": lexical,
                "_any_unresolved": any_unresolved,
            }
        )

    pertinent_count = sum(1 for r in rows_out if r["pertinent_age_fer"])
    lexical_count = sum(1 for r in rows_out if r["pertinent_age_fer_lexical"])
    entries_any_unresolved = sum(1 for r in rows_out if r["_any_unresolved"])
    for r in rows_out:
        del r["_any_unresolved"]

    def _pert_reason(r: dict) -> str:
        has_p = bool(r["periode_match"])
        has_t = bool(r["type_site_match"]) and any(
            x in _STRONG_IRON_TYPES for x in r["type_site_match"].split(";") if x
        )
        # commune seul : pertinent mais pas lexical
        if r["pertinent_age_fer"] and not r["pertinent_age_fer_lexical"]:
            return "commune_notice_uniquement"
        if has_p and has_t:
            return "periode_et_type"
        if has_p:
            return "periode_ou_cross"
        if has_t:
            return "type_site_fort"
        return "autre"

    reason_counts: dict[str, int] = {}
    for r in rows_out:
        if r["pertinent_age_fer"]:
            k = _pert_reason(r)
            reason_counts[k] = reason_counts.get(k, 0) + 1

    fieldnames = [
        "terme",
        "communes_ref",
        "communes_noms",
        "nb_refs",
        "cross_refs",
        "categorie",
        "toponyme_match",
        "periode_match",
        "type_site_match",
        "confidence",
        "pertinent_age_fer",
        "pertinent_age_fer_lexical",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r[k] for k in fieldnames})

    report = {
        "source": "data/analysis/cag_68_index/index_entries.json",
        "communes_join": "data/analysis/cag_68_texte/communes.json",
        "counts": {
            "entries": len(rows_out),
            "commune_reference_slots": total_ref_slots,
            "commune_reference_slots_resolved": resolved_ref_slots,
            "resolution_rate_refs": round(
                resolved_ref_slots / total_ref_slots, 4
            )
            if total_ref_slots
            else 0,
            "entries_with_any_unresolved_commune": entries_any_unresolved,
            "toponyme_hits": sum(1 for r in rows_out if r["toponyme_match"]),
            "periode_hits": sum(1 for r in rows_out if r["periode_match"]),
            "type_site_hits": sum(1 for r in rows_out if r["type_site_match"]),
            "pertinent_age_fer": pertinent_count,
            "pertinent_age_fer_lexical": lexical_count,
        },
        "iron_age_breakdown": reason_counts,
        "unresolved_commune_codes": dict(
            sorted(unresolved_codes.items(), key=lambda x: -x[1])
        ),
        "confidence_distribution": {
            k: sum(1 for r in rows_out if r["confidence"] == k)
            for k in ("HIGH", "MEDIUM", "LOW")
        },
        "categorie_distribution": {},
        "iron_age_summary": {
            "definition": (
                "Pertinent si : période (terme ou cross_refs) selon periodes.json ; "
                "ou au moins une commune référencée avec Hallstatt/La Tène dans "
                "periodes_mentionnees (communes.json) ; ou type_site ∈ "
                f"{sorted(_STRONG_IRON_TYPES)} (aliases types_sites.json). "
                "HABITAT et VOIE seuls ne suffisent pas (trop génériques / romains)."
            ),
            "count_entries": pertinent_count,
            "sample_termes": [
                r["terme"]
                for r in rows_out
                if r["pertinent_age_fer"]
            ][:40],
            "sample_termes_lexical_seulement": [
                r["terme"]
                for r in rows_out
                if r["pertinent_age_fer_lexical"]
            ][:40],
        },
        "limits": [
            "10 codes INSEE présents dans l'index mais absents de communes.json "
            "(fusion / découpage / erreur de numérotation CAG).",
            "Les concordances toponymiques sont des sous-chaînes du lemme ; "
            "faux positifs possibles sur noms très courts.",
        ],
    }
    cat_dist: dict[str, int] = {}
    for r in rows_out:
        cat_dist[r["categorie"]] = cat_dist.get(r["categorie"], 0) + 1
    report["categorie_distribution"] = cat_dist

    OUT_REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Écrit {OUT_CSV} ({len(rows_out)} lignes)")
    print(f"Écrit {OUT_REPORT}")
    print(
        f"Résolution renvois communes : {resolved_ref_slots}/{total_ref_slots} "
        f"({100 * resolved_ref_slots / total_ref_slots:.2f}%)"
    )
    print(f"Entrées pertinentes âge du Fer : {pertinent_count}")
    print(f"  dont signal lexical (période/types forts) : {lexical_count}")


if __name__ == "__main__":
    main()
