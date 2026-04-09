# Design — Ingestion BdD Proto Alsace

## Stack

- Python 3.9+, `pandas`, `openpyxl` (Proto XLSX), `python-calamine` (Alsace_Basel_AF XLSX — openpyxl fails on embedded validation), `pyproj` (WGS84 → EPSG:2154), `rapidfuzz` (optional fuzzy lieu-dit / dedup).

## Paths

- `ROOT` = repo root (two levels above `ingest.py`).
- Script: `data/analysis/BdD_Proto_Alsace (1)/ingest.py`.
- Outputs: same folder + `quality_report.json`.

## Pipeline

1. **T1** — Load Proto; assert 1127×23; drop empty columns; strip text fields; flags NaN→0, 1.0→1.
2. **T2** — `included_fer_policy`: true if Fer flags (LTAB/LTCD/HaD/BF3_HaC) or text matches `periodes.json` patterns / Ha / LT / Bze D–Ha bridges; exclude rows that are *only* Bronze ancien/moyen with no Fer signal.
3. **T3** — Map `type_site` to canonical enum (NECROPOLE/TUMULUS/HABITAT/OPPIDUM/DEPOT/SANCTUAIRE/INDETERMINE) using rules + `types_sites.json` token checks on `structures`; `statut_fouille` from `type_oa`; period from `datation_2` priority.
4. **T4** — Build normalized `(commune, lieu_dit)` index from Alsace_Basel `sites` sheet (engine `calamine`); exact match then fuzzy lieu-dit within commune (score ≥ 82); WGS84 → L93; no coords if no match.
5. **T5** — Fuzzy match `commune|lieu_dit` and optional biblio token overlap vs `data/output/sites_cleaned.csv` and `data/sources/golden_sites.csv`.
6. **T6** — Export filtered rows to CSV; JSON quality report with counts and lists.

## Fer policy (documented in JSON)

Strict Fer relevance: export only rows with `included_fer_policy == True`.
