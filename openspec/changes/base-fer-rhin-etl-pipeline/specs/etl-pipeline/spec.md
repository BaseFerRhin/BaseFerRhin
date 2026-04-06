## ADDED Requirements

### Requirement: 8-step pipeline orchestration
The system SHALL orchestrate an ETL pipeline with 8 sequential steps: DISCOVER, INGEST, EXTRACT, NORMALIZE, DEDUPLICATE, GEOCODE, VALIDATE, EXPORT. Each step SHALL accept the output of the previous step and produce input for the next. The pipeline SHALL be invocable via a single entry point `run_pipeline(config: PipelineConfig)`.

#### Scenario: Full pipeline execution
- **WHEN** `run_pipeline` is called with a config pointing to Gallica CAG 67 as source
- **THEN** the pipeline SHALL execute all 8 steps in order and produce output files in `data/output/`

#### Scenario: Partial pipeline from a specific step
- **WHEN** `run_pipeline` is called with `start_from="NORMALIZE"`
- **THEN** the pipeline SHALL load intermediate results from `data/processed/` and resume from the NORMALIZE step

### Requirement: Idempotent execution
Each pipeline step SHALL be idempotent: running the same step twice with the same input SHALL produce the same output without creating duplicates. Intermediate results SHALL be stored in `data/processed/` with checksums to detect changes.

#### Scenario: Re-run without changes
- **WHEN** the full pipeline is run twice with identical sources
- **THEN** the second run SHALL detect no changes and skip re-processing (via checksum comparison)

#### Scenario: Incremental new source
- **WHEN** a new CSV source is added after a first pipeline run
- **THEN** only the new source SHALL be processed through EXTRACT→NORMALIZE, then merged with existing data at DEDUPLICATE

### Requirement: Pipeline configuration
The system SHALL accept a `PipelineConfig` (Pydantic model) with fields: `sources` (list of source configs), `gallica_queries` (list of SRU queries), `ocr_quality_threshold` (float, default 0.4), `dedup_merge_threshold` (float, default 0.85), `dedup_review_threshold` (float, default 0.70), `geocoder_cache_path` (Path), `output_dir` (Path), `log_level` (str).

#### Scenario: Custom thresholds
- **WHEN** the config sets `dedup_merge_threshold=0.90`
- **THEN** the deduplicator SHALL use 90% as the automatic merge threshold

### Requirement: Structured logging and audit trail
Each pipeline step SHALL log: step name, start/end timestamps, input count, output count, error count, and any warnings. Logs SHALL be written to both console (via `rich`) and a JSON log file at `data/processed/pipeline_log.json`.

#### Scenario: Log output after pipeline run
- **WHEN** a pipeline run completes
- **THEN** `pipeline_log.json` SHALL contain one entry per step with timing, counts, and error details

### Requirement: Error queue for manual review
Sites that fail any step (OCR unreadable, normalization ambiguous, geocoding failed, validation error) SHALL be collected in a review queue at `data/processed/review_queue.json`. Each entry SHALL include the site data, the step where failure occurred, and the reason.

#### Scenario: OCR failure queued
- **WHEN** a Gallica page has OCR confidence below threshold
- **THEN** the page SHALL be added to the review queue with `step="EXTRACT"` and `reason="ocr_confidence_below_threshold"`

#### Scenario: Geocoding failure queued
- **WHEN** a site cannot be geocoded by any API
- **THEN** the site SHALL be added to the review queue with `step="GEOCODE"` and `reason="all_geocoders_failed"`

### Requirement: Chronological and geographical validation
The VALIDATE step SHALL check: (1) `datation_debut` <= `datation_fin` when both are present, (2) Hallstatt dates are within -800 to -450, La Tène dates within -450 to -25, (3) coordinates fall within the expected bounding box (lat 47.0–49.5, lon 6.5–9.0 for the Upper Rhine region).

#### Scenario: Date inversion detected
- **WHEN** a site has `datation_debut=-300` and `datation_fin=-500`
- **THEN** the validator SHALL flag the site with warning "datation_debut > datation_fin"

#### Scenario: Coordinates outside region
- **WHEN** a site has `latitude=52.0` (Berlin area) but `region_admin="Alsace"`
- **THEN** the validator SHALL flag the site with warning "coordinates outside expected region"
