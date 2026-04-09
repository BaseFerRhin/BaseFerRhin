# Tasks — ingest-bdd-proto-alsace-1

- [x] T1 — Load Proto XLSX, validate shape, drop `type_precision`/`conservati`, strip text, normalize BA…LTCD flags
- [x] T2 — Compute `included_fer_policy` (flags + period text; exclude BA/BM-only without Fer signal)
- [x] T3 — Classify `type_site_canon`, `statut_fouille`, `periode` / `sous_periode` via references
- [x] T4 — Spatial join to Alsace_Basel_AF (`calamine`), WGS84 → L93, confiance rules
- [x] T5 — Dedup hints vs `sites_cleaned.csv` and `golden_sites.csv` (fuzzy + biblio)
- [x] T6 — Write `sites_cleaned.csv` and `quality_report.json`; run script and validate counts
