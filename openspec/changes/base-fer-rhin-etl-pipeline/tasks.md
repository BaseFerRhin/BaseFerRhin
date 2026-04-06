## 1. Project Setup

- [x] 1.1 Create Python project structure (`src/domain/`, `src/infrastructure/`, `src/application/`, `data/`, `tests/`)
- [x] 1.2 Create `pyproject.toml` with dependencies: pydantic, httpx, pdfplumber, rapidfuzz, geopy, lxml, geopandas, sqlite-utils, rich, tenacity, pytest, pytest-asyncio, respx
- [x] 1.3 Create `__init__.py` files for all packages
- [x] 1.4 Create `README.md` with project overview, setup instructions, and usage examples

## 2. Domain Model (spec: domain-model)

- [x] 2.1 Implement `TypeSite` enum (OPPIDUM, HABITAT, NECROPOLE, DEPOT, SANCTUAIRE, ATELIER, VOIE, TUMULUS, INDETERMINE) in `src/domain/models/enums.py`
- [x] 2.2 Implement `Periode` enum (HALLSTATT, LA_TENE, TRANSITION, INDETERMINE) with serialization to display names in `src/domain/models/enums.py`
- [x] 2.3 Implement `NiveauConfiance`, `PrecisionLocalisation`, `StatutFouille` enums in `src/domain/models/enums.py`
- [x] 2.4 Implement `PhaseOccupation` Pydantic model with period/sub-period validation in `src/domain/models/phase.py`
- [x] 2.5 Implement `Source` Pydantic model with Gallica-specific fields (ark, page, confiance_ocr) in `src/domain/models/source.py`
- [x] 2.6 Implement `Site` Pydantic root aggregate with auto-timestamps and prefixed site_id in `src/domain/models/site.py`
- [x] 2.7 Implement `RawRecord` dataclass as intermediate extraction format in `src/domain/models/raw_record.py`
- [x] 2.8 Write unit tests for all models: valid creation, missing field rejection, invalid enum rejection, multi-phase site in `tests/domain/test_models.py`

## 3. Reference Data (spec: site-normalizer)

- [x] 3.1 Create `data/reference/types_sites.json` — alias→TypeSite lookup dictionary (FR + DE aliases)
- [x] 3.2 Create `data/reference/periodes.json` — period patterns and sub-period mappings (FR + DE)
- [x] 3.3 Create `data/reference/toponymes_fr_de.json` — bilingual commune concordance (Alsace + Basel)
- [x] 3.4 Create `data/reference/gallica_sources.json` — ARK IDs, SRU queries, metadata for CAG 67, CAG 68, Cahiers alsaciens

## 4. Site Normalizers (spec: site-normalizer)

- [x] 4.1 Implement `TypeSiteNormalizer` with case-insensitive alias lookup and INDETERMINE fallback in `src/domain/normalizers/type_site.py`
- [x] 4.2 Implement `PeriodeNormalizer` with regex patterns for period/sub-period extraction (FR + DE) in `src/domain/normalizers/periode.py`
- [x] 4.3 Implement `ToponymeNormalizer` with bidirectional FR↔DE resolution and variant accumulation in `src/domain/normalizers/toponymie.py`
- [x] 4.4 Implement composite `SiteNormalizer` applying type→period→toponym in sequence in `src/domain/normalizers/composite.py`
- [x] 4.5 Write unit tests: FR alias→OPPIDUM, DE alias→NECROPOLE, "Ha D2-D3" sub-period extraction, "Schlettstadt"→"Sélestat" resolution in `tests/domain/test_normalizers.py`

## 5. Domain Validators (spec: etl-pipeline)

- [x] 5.1 Implement chronological coherence validator (datation_debut <= datation_fin, period date ranges) in `src/domain/validators/coherence_chrono.py`
- [x] 5.2 Implement geographical coherence validator (coordinates within Upper Rhine bounding box 47.0–49.5 / 6.5–9.0) in `src/domain/validators/coherence_geo.py`
- [x] 5.3 Implement sub-period/period consistency validator (e.g., LT sub-period under Hallstatt → flag) in `src/domain/validators/coherence_chrono.py`
- [x] 5.4 Write unit tests for validators: date inversion, out-of-region coords, period/sub-period mismatch in `tests/domain/test_validators.py`

## 6. Gallica Extractor (spec: gallica-extractor)

- [x] 6.1 Implement `GallicaSRUClient` with CQL query builder, XML response parsing, ARK extraction, pagination in `src/infrastructure/extractors/gallica_sru.py`
- [x] 6.2 Implement `GallicaOCRClient` with page-level text download, retry logic, error handling in `src/infrastructure/extractors/gallica_ocr.py`
- [x] 6.3 Implement OCR quality scorer (dictionary word ratio → confidence float) in `src/infrastructure/extractors/gallica_ocr.py`
- [x] 6.4 Implement `GallicaALTOClient` with ALTO XML parsing and text block extraction with coordinates in `src/infrastructure/extractors/gallica_alto.py`
- [x] 6.5 Implement `GallicaIIIFClient` for image download and local caching in `src/infrastructure/extractors/gallica_iiif.py`
- [x] 6.6 Implement rate limiter (asyncio.Semaphore max 5 concurrent) and local file cache in `src/infrastructure/extractors/gallica_cache.py`
- [x] 6.7 Implement `GallicaSiteMentionExtractor` with regex patterns for commune+type extraction from OCR text in `src/infrastructure/extractors/gallica_mention_extractor.py`
- [x] 6.8 Implement facade `GallicaExtractor` composing SRU→OCR→mention extraction, producing list[RawRecord] in `src/infrastructure/extractors/gallica_extractor.py`
- [x] 6.9 Write integration tests with HTTP mocks (respx): SRU search, OCR download, ALTO parse, cache behavior in `tests/infrastructure/test_gallica.py`

## 7. Source Extractors (spec: source-extractors)

- [x] 7.1 Define `SourceExtractor` protocol (extract, supported_formats) in `src/infrastructure/extractors/base.py`
- [x] 7.2 Implement `PDFExtractor` via pdfplumber (text + table extraction, needs_ocr flag) in `src/infrastructure/extractors/pdf_extractor.py`
- [x] 7.3 Implement `CSVExtractor` with configurable column mapping, encoding detection, multi-delimiter support in `src/infrastructure/extractors/csv_extractor.py`
- [x] 7.4 Implement extractor dispatch factory (file extension → extractor) in `src/infrastructure/extractors/factory.py`
- [x] 7.5 Write tests for PDF and CSV extractors with fixture files in `tests/infrastructure/test_extractors.py`

## 8. Multi-Geocoder (spec: multi-geocoder)

- [x] 8.1 Define `Geocoder` protocol and `GeoResult` dataclass in `src/infrastructure/geocoding/base.py`
- [x] 8.2 Implement `BANGeocoder` (api-adresse.data.gouv.fr) for French sites in `src/infrastructure/geocoding/ban.py`
- [x] 8.3 Implement `NominatimGeocoder` with country restriction and 1 req/s rate limit in `src/infrastructure/geocoding/nominatim.py`
- [x] 8.4 Implement `GeoAdminGeocoder` (geo.admin.ch) for Swiss sites in `src/infrastructure/geocoding/geo_admin.py`
- [x] 8.5 Implement `MultiGeocoder` facade with country-adaptive dispatch, fallback chain, and centroid fallback in `src/infrastructure/geocoding/multi_geocoder.py`
- [x] 8.6 Implement geocoding cache (JSON file) for commune-level results in `src/infrastructure/geocoding/cache.py`
- [x] 8.7 Write tests with mocked HTTP responses for each geocoder in `tests/infrastructure/test_geocoding.py`

## 9. Site Deduplicator (spec: site-deduplicator)

- [x] 9.1 Implement composite similarity scorer (name 40% + commune 30% + geo distance 30%) using rapidfuzz + Haversine in `src/domain/deduplication/scorer.py`
- [x] 9.2 Implement merge strategy (richest record primary, accumulate sources + name variants) in `src/domain/deduplication/merger.py`
- [x] 9.3 Implement `SiteDeduplicator` with configurable merge/review thresholds and report generation in `src/domain/deduplication/deduplicator.py`
- [x] 9.4 Write tests: FR/DE variant merge, ambiguous pair flagging, distant homophone rejection in `tests/domain/test_deduplication.py`

## 10. Persistence and Export (spec: data-export)

- [x] 10.1 Implement `SQLiteRepository` with 3 tables (sites, phases, sources), foreign keys, indexes via sqlite-utils in `src/infrastructure/persistence/sqlite_repository.py`
- [x] 10.2 Implement `GeoJSONExporter` via geopandas with EPSG:4326, phase flattening, coordinate-less site exclusion in `src/infrastructure/persistence/geojson_exporter.py`
- [x] 10.3 Implement `CSVExporter` with denormalized rows (1 row per site-phase), UTF-8 BOM, source references in `src/infrastructure/persistence/csv_exporter.py`
- [x] 10.4 Implement export summary statistics (counts by pays, periode, type_site) via rich table in `src/infrastructure/persistence/stats.py`
- [x] 10.5 Write tests: SQLite FK integrity, GeoJSON validity, CSV row count for multi-phase sites in `tests/infrastructure/test_export.py`

## 11. Pipeline Orchestration (spec: etl-pipeline)

- [x] 11.1 Implement `PipelineConfig` Pydantic model with all configurable parameters in `src/application/config.py`
- [x] 11.2 Implement pipeline step runner with structured logging (rich console + JSON file) in `src/application/pipeline.py`
- [x] 11.3 Implement idempotency via checksum-based change detection on intermediate files in `src/application/pipeline.py`
- [x] 11.4 Implement review queue collector (JSON output with step, reason, site data) in `src/application/review_queue.py`
- [x] 11.5 Implement CLI entry point (`python -m baseferrhin.pipeline --config config.yaml`) in `src/__main__.py`
- [x] 11.6 Create sample `config.yaml` with Gallica CAG 67 + CAG 68 as default sources
- [x] 11.7 Write integration test: full pipeline on 5 fixture sites (mock Gallica + local CSV) in `tests/test_pipeline_integration.py`

## 12. Golden Dataset and Acceptance Tests

- [x] 12.1 Create golden dataset of 20 known Iron Age sites (Breisach, Münsterhügel Basel, Haguenau tumuli, etc.) in `tests/fixtures/golden_sites.json`
- [x] 12.2 Write acceptance tests matching the 6 criteria from the prompt (valid Pydantic model, Gallica OCR extraction, "Höhensiedlung"→OPPIDUM, Breisach dedup, GeoJSON valid, pipeline <10 min) in `tests/test_acceptance.py`
