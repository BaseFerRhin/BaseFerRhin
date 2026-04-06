## ADDED Requirements

### Requirement: GeoJSON export compatible with QGIS
The system SHALL export the normalized site inventory as a GeoJSON FeatureCollection using `geopandas`. Each Feature SHALL have: geometry (Point from lat/lon), and properties including all Site fields plus flattened PhaseOccupation and Source summaries. The GeoJSON SHALL use CRS EPSG:4326 (WGS84). Output path: `data/output/sites_age_fer.geojson`.

#### Scenario: Valid GeoJSON generation
- **WHEN** the export step runs on 100 validated sites
- **THEN** the output file SHALL be valid GeoJSON parseable by `json.loads()` and openable in QGIS

#### Scenario: Sites without coordinates excluded from GeoJSON
- **WHEN** a site has `latitude=None` and `longitude=None`
- **THEN** the site SHALL NOT appear in the GeoJSON export (but SHALL appear in CSV and SQLite)

#### Scenario: PhaseOccupation flattened in properties
- **WHEN** a site has 2 PhaseOccupation entries
- **THEN** the GeoJSON properties SHALL include `periodes` as a comma-separated string (e.g., "Hallstatt D, La Tène A")

### Requirement: CSV export with full detail
The system SHALL export a denormalized CSV file where each row represents one Site-PhaseOccupation combination. A site with 2 phases SHALL produce 2 CSV rows. Output path: `data/output/sites_age_fer.csv`. Encoding SHALL be UTF-8 with BOM for Excel compatibility.

#### Scenario: Multi-phase site produces multiple rows
- **WHEN** site "Breisach" has Hallstatt D and La Tène A phases
- **THEN** the CSV SHALL contain 2 rows for "Breisach", each with the corresponding phase fields

#### Scenario: CSV includes source references
- **WHEN** a site has 3 sources
- **THEN** the CSV SHALL include a `sources_count` field and a `source_references` field with semicolon-separated references

### Requirement: SQLite export with relational schema
The system SHALL export a SQLite database with 3 tables: `sites`, `phases`, `sources` with proper foreign keys. The database SHALL include indexes on `site_id`, `commune`, `type_site`, `periode`. Output path: `data/output/sites_age_fer.sqlite`.

#### Scenario: Relational integrity
- **WHEN** the SQLite database is exported
- **THEN** every `phases.site_id` SHALL reference an existing `sites.site_id` and every `sources.site_id` SHALL reference an existing `sites.site_id`

#### Scenario: Queryable by period and type
- **WHEN** a SQL query `SELECT * FROM sites JOIN phases ON sites.site_id = phases.site_id WHERE phases.periode = 'Hallstatt' AND sites.type_site = 'OPPIDUM'` is executed
- **THEN** the result SHALL return all Hallstatt oppida in the inventory

### Requirement: Export summary statistics
After export, the system SHALL print and log summary statistics: total sites, sites per country, sites per period, sites per type, sites with/without coordinates, sites in review queue.

#### Scenario: Summary statistics output
- **WHEN** export completes on 200 sites
- **THEN** the system SHALL display a table with counts by pays (FR/DE/CH), by periode (HALLSTATT/LA_TENE/TRANSITION/INDETERMINE), and by type_site
