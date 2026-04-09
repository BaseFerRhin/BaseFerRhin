## ADDED Requirements

### Requirement: Generate metadata JSON for each input file
The system SHALL analyze each CSV file in `data/input/` and produce a `metadata.json` file in `data/analysis/<file_stem>/` containing the complete technical profile of the file.

#### Scenario: Metadata generation for a standard ArkeoGIS CSV
- **WHEN** the analysis script is executed on a CSV file with ArkeoGIS schema (22 columns, `;` separator)
- **THEN** a `metadata.json` file SHALL be created containing: file_name, file_path, format, separator, encoding, total_rows, total_columns, and a columns array

#### Scenario: Column profiling
- **WHEN** a metadata.json is generated
- **THEN** each entry in the columns array SHALL contain: name, dtype, null_count, null_pct, unique_count, and sample_values (top 3 non-null values)

### Requirement: Metadata SHALL include source provenance
The system SHALL extract and record the data source provenance from the file content itself.

#### Scenario: ArkeoGIS source extraction
- **WHEN** the file contains a DATABASE_NAME column
- **THEN** metadata.json SHALL include a `source` object with `platform` ("ArkeoGIS"), `database_name` (value from first row), and `export_date` (parsed from filename pattern YYYYMMDD)

### Requirement: Metadata SHALL include geographic extent
The system SHALL compute the geographic bounding box from the coordinate columns.

#### Scenario: Bounding box computation
- **WHEN** the file contains LATITUDE and LONGITUDE columns with numeric values
- **THEN** metadata.json SHALL include a `geographic` object with `projection` ("EPSG:4326"), `min_lat`, `max_lat`, `min_lon`, `max_lon`

#### Scenario: City centroid ratio
- **WHEN** the file contains a CITY_CENTROID column
- **THEN** the `geographic` object SHALL include `city_centroid_pct` (percentage of rows where CITY_CENTROID equals "Oui")

### Requirement: Metadata SHALL include chronological profile
The system SHALL analyze the date columns to profile the chronological coverage.

#### Scenario: Period range extraction
- **WHEN** STARTING_PERIOD and ENDING_PERIOD columns contain values in format `-YYYY:-YYYY`
- **THEN** metadata.json SHALL include a `chronology` object with `earliest` (minimum start year) and `latest` (maximum end year)

#### Scenario: Indeterminate period counting
- **WHEN** STARTING_PERIOD contains values "Indéterminé"
- **THEN** `chronology` SHALL include `indeterminate_rows` (count) and `indeterminate_pct`

### Requirement: Metadata SHALL include quality assessment
The system SHALL compute a quality assessment based on completeness and consistency checks.

#### Scenario: Completeness metrics
- **WHEN** metadata is generated
- **THEN** a `quality` object SHALL include `lat_lon_filled_pct`, `period_filled_pct`, `bibliography_filled_pct`

#### Scenario: Quality issues detection
- **WHEN** the file contains malformed values (double-escaped quotes `""""`, coordinates at 0, periods outside [-3000, 100])
- **THEN** the `quality.issues` array SHALL list each detected anomaly with a description

#### Scenario: Confidence level assignment
- **WHEN** quality metrics are computed
- **THEN** `quality.confidence_level` SHALL be "HIGH" if completeness > 80% and no critical issues, "MEDIUM" if completeness 50-80%, "LOW" otherwise

### Requirement: Metadata SHALL describe the data model grain
The system SHALL document the multi-row-per-site grain of ArkeoGIS data.

#### Scenario: Grain documentation
- **WHEN** a file has multiple rows with the same SITE_AKG_ID
- **THEN** metadata.json SHALL include a `data_model` object with `grain` description, `rows_per_site_avg`, `rows_per_site_max`, and `unique_sites_count`
