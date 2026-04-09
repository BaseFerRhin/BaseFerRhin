## ADDED Requirements

### Requirement: Relational schema creation

The system SHALL create a DuckDB database with 6 tables: `communes` (PK commune_id), `notices` (PK notice_id, FK commune_id, includes `confidence_level` VARCHAR), `periodes` (FK notice_id, includes `periode_norm` VARCHAR for normalized period), `vestiges` (FK notice_id), `bibliographie` (FK notice_id), `figures` (FK notice_id). All FK constraints SHALL use REFERENCES. Schema creation MUST be idempotent (CREATE TABLE IF NOT EXISTS).

#### Scenario: Fresh database creation
- **WHEN** no database file exists at the configured path
- **THEN** all 6 tables and 4 views are created in a new DuckDB file

#### Scenario: Idempotent schema application
- **WHEN** the schema is applied to an existing database with tables already present
- **THEN** no error occurs and existing data is preserved

### Requirement: Analytical views

The system SHALL create 5 views: `v_fer_notices` (Iron Age notices with commune coordinates), `v_stats_by_commune` (counts per commune), `v_stats_by_type` (counts per site type), `v_stats_by_periode` (counts per period using `periode_norm`), `v_period_cooccurrence` (period co-occurrence matrix via self-join on periodes).

#### Scenario: v_fer_notices view
- **WHEN** querying `v_fer_notices`
- **THEN** only notices where `has_iron_age = true` are returned, joined with commune lat/lon

#### Scenario: v_stats_by_commune aggregation
- **WHEN** querying `v_stats_by_commune`
- **THEN** each row contains commune_id, commune_name, total_notices, fer_notices, and type_count

#### Scenario: v_period_cooccurrence matrix
- **WHEN** querying `v_period_cooccurrence`
- **THEN** each row contains period_a, period_b (normalized), and co_count representing how many notices mention both periods

### Requirement: Record loading into DuckDB

The system SHALL insert `SiteRecord` objects into the appropriate DuckDB tables, generating `notice_id` as `CAG67-{commune_id}-{sous_notice_code}`. Loading MUST handle duplicates via `INSERT INTO ... ON CONFLICT (notice_id) DO UPDATE SET ...` or a transactional DELETE/INSERT pattern (DuckDB does not support `INSERT OR REPLACE`).

#### Scenario: Insert a single SiteRecord
- **WHEN** a SiteRecord with commune_id="002", code="007" is loaded
- **THEN** a row with notice_id="CAG67-002-007" is inserted into `notices`, and related rows are inserted into `periodes`, `vestiges`, `bibliographie`, `figures`

#### Scenario: Re-running extraction (idempotent load)
- **WHEN** extraction is re-run on the same PDF
- **THEN** existing records are replaced and the total count remains stable

### Requirement: Commune data loading

The system SHALL insert commune metadata (id, name, page range) into the `communes` table and update coordinates after geocoding.

#### Scenario: Commune insertion
- **WHEN** commune 002 — Achenheim spans pages 155–156
- **THEN** a row is inserted with `commune_id="002"`, `commune_name="Achenheim"`, `page_start=155`, `page_end=156`

#### Scenario: Coordinate update after geocoding
- **WHEN** geocoding returns lat=48.58, lon=7.60 for commune 002
- **THEN** the `communes` row is updated with `latitude=48.58`, `longitude=7.60`

### Requirement: Analytical queries module

The system SHALL provide pre-defined SQL query functions in `queries.py` for: total counts, Iron Age counts by commune, top communes by notice count, period distribution (using `periode_norm`), vestige frequency, full-text search, period co-occurrence matrix, and extraction quality metrics (coverage rate, notice length distribution).

#### Scenario: Top communes query
- **WHEN** calling `top_communes(db, limit=20, iron_age_only=True)`
- **THEN** the 20 communes with the most Iron Age notices are returned with counts

#### Scenario: Full-text search
- **WHEN** calling `search_notices(db, query="tumulus Hallstatt")`
- **THEN** notices whose `full_text` contains both "tumulus" and "Hallstatt" are returned

#### Scenario: Period co-occurrence query
- **WHEN** calling `period_cooccurrence(db)`
- **THEN** a list of (period_a, period_b, co_count) tuples is returned from `v_period_cooccurrence`

#### Scenario: Extraction quality metrics
- **WHEN** calling `extraction_metrics(db)`
- **THEN** a dict is returned with: total_pages_processed, total_communes, total_notices, iron_age_notices, coverage_rate, avg_notice_length, median_notice_length
