## ADDED Requirements

### Requirement: Generate an executable ingestion prompt per file
The system SHALL produce an `ingestion_prompt.md` file in `data/analysis/<file_stem>/` that an AI agent can execute autonomously to ingest the file into BaseFerRhin.

#### Scenario: Prompt structure
- **WHEN** ingestion_prompt.md is generated
- **THEN** it SHALL contain: Contexte (project + file summary), Références obligatoires (paths to reference files), and Tasks T1 through T6

### Requirement: Prompt T1 — Loading and cleaning
The ingestion prompt SHALL specify CSV loading parameters and cleaning steps.

#### Scenario: T1 content
- **WHEN** T1 is defined
- **THEN** it SHALL specify: pandas read_csv parameters (sep, encoding), cleaning of malformed quotes, normalization of SITE_NAME and MAIN_CITY_NAME, parsing of date format `-YYYY:-YYYY`, handling of "Indéterminé" values

### Requirement: Prompt T2 — Site aggregation
The ingestion prompt SHALL specify how to collapse multi-row ArkeoGIS records into one record per site.

#### Scenario: T2 content
- **WHEN** T2 is defined
- **THEN** it SHALL specify: grouping key (SITE_AKG_ID), aggregation of CARAC_* columns into a list, deduplication and concatenation of BIBLIOGRAPHY, union of STARTING/ENDING_PERIOD ranges

### Requirement: Prompt T3 — Classification
The ingestion prompt SHALL specify the classification logic for type, period, and confidence.

#### Scenario: T3 type mapping
- **WHEN** T3 maps site types
- **THEN** it SHALL provide the explicit mapping from CARAC_LVL1 values to normalized types using `types_sites.json` (Enceinte → OPPIDUM, Habitat → HABITAT, Funéraire → NECROPOLE, etc.)

#### Scenario: T3 confidence scoring
- **WHEN** T3 assigns confidence
- **THEN** it SHALL use: HIGH if STATE_OF_KNOWLEDGE="Fouillé" AND CITY_CENTROID="Non", MEDIUM if "Sondé" or "Littérature", LOW if CITY_CENTROID="Oui" or "Non renseigné"

### Requirement: Prompt T4 — Geocoding and projection
The ingestion prompt SHALL specify coordinate validation and projection.

#### Scenario: T4 content
- **WHEN** T4 is defined
- **THEN** it SHALL specify: bounding box validation (lat 47-50, lon 7-11), projection from EPSG:4326 to EPSG:2154 (Lambert-93) using pyproj, flagging of centroid coordinates

### Requirement: Prompt T5 — Cross-source deduplication
The ingestion prompt SHALL specify how to detect duplicates against existing data.

#### Scenario: T5 content
- **WHEN** T5 is defined
- **THEN** it SHALL specify: comparison targets (data/output/sites.csv, data/sources/golden_sites.csv), matching criteria (distance < 500m AND same commune, OR fuzzy name match > 0.85), output as review queue

### Requirement: Prompt T6 — Export
The ingestion prompt SHALL specify the output format.

#### Scenario: T6 content
- **WHEN** T6 is defined
- **THEN** it SHALL specify: output path `data/analysis/<file_stem>/sites_cleaned.csv` with normalized schema, and a `quality_report.json` summarizing anomalies and counts
