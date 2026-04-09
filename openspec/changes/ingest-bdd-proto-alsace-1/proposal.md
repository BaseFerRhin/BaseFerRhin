# Proposal — Ingestion BdD Proto Alsace

## What

Ingest `data/input/BdD_Proto_Alsace (1).xlsx` (1127 sites, no native coordinates) into `sites_cleaned.csv` and `quality_report.json` under `data/analysis/BdD_Proto_Alsace (1)/`, following the six-task pipeline (T1–T6).

## Why

Enrich the BaseFerRhin iron-age inventory with Alsace protohistoric sites: Fer-relevant filtering, canonical types/periods from project references, optional coordinates via join to `Alsace_Basel_AF (1).xlsx`, and deduplication hints against existing exports and golden sites.

## Source quality

- Metadata confidence LOW (~41.5% fill); two columns 100% empty (`type_precision`, `conservati`).
- Unique key: `id` (1127 uniques).

## Out of scope

- Inventing coordinates without join or geocoding.
- Patriarche EA join for coordinates: `20250806_Patriarche_ageFer.xlsx` has no XY columns; EA numeric codes in Proto do not align with `Numero_de_l_EA` format — documented in quality report only.
