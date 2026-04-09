## ADDED Requirements

### Requirement: Export Iron Age notices to RawRecord JSON

The system SHALL export all Iron Age notices from DuckDB as a JSON array of dictionaries compatible with BaseFerRhin's `RawRecord` dataclass. Each record MUST include: source_label "cag_67", commune name, lieu-dit, site type, periods, coordinates, and raw text.

#### Scenario: Successful export
- **WHEN** running `python -m src export --format raw-records --output path/to/output.json`
- **THEN** a JSON file is written containing one dict per Iron Age notice with all required fields

#### Scenario: Export with iron_age_only flag
- **WHEN** exporting with `iron_age_only=True` (default)
- **THEN** only notices where `has_iron_age = true` are included

#### Scenario: Export all notices
- **WHEN** exporting with `--all` flag
- **THEN** all notices (not just Iron Age) are included in the output

### Requirement: CLI commands

The system SHALL provide a Click CLI with commands: `extract` (PDF → DuckDB), `geocode` (commune geocoding), `export` (DuckDB → JSON), `stats` (quick statistics to terminal).

#### Scenario: Extract command
- **WHEN** running `python -m src extract --pdf path/to/pdf`
- **THEN** the full extraction pipeline runs and creates/updates `data/cag67.duckdb`

#### Scenario: Geocode command
- **WHEN** running `python -m src geocode`
- **THEN** all communes in DuckDB are geocoded via BAN API

#### Scenario: Stats command
- **WHEN** running `python -m src stats`
- **THEN** a Rich-formatted summary table is printed to stdout with total communes, notices, Iron Age counts, and top 10 communes

#### Scenario: Export command
- **WHEN** running `python -m src export --format raw-records --output output.json`
- **THEN** the export runs and prints the number of records exported
