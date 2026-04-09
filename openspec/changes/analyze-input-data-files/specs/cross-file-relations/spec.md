## ADDED Requirements

### Requirement: Generate a cross-file relations document
The system SHALL produce a `CROSS_FILE_RELATIONS.md` file in `data/analysis/` that documents relationships between all files in `data/input/`.

#### Scenario: Document creation
- **WHEN** individual file analyses are complete
- **THEN** a `data/analysis/CROSS_FILE_RELATIONS.md` SHALL be created covering: schema comparison, geographic overlap, chronological complementarity, typological complementarity, links to existing project sources, and fusion strategy

### Requirement: Document shared schema
The system SHALL compare column schemas across files and document differences.

#### Scenario: Schema comparison
- **WHEN** both files share the ArkeoGIS schema
- **THEN** the document SHALL list identical columns, and highlight fill-rate differences (e.g., BIBLIOGRAPHY filled at 95% in LoupBernard vs 30% in ADAB2011)

### Requirement: Analyze geographic overlap
The system SHALL identify sites that appear in multiple files based on spatial proximity.

#### Scenario: Overlap detection
- **WHEN** two files contain sites within 1 km of each other
- **THEN** the document SHALL list the number of spatially close pairs and identify likely duplicates (same MAIN_CITY_NAME + distance < 500m)

#### Scenario: Bounding box comparison
- **WHEN** geographic extents are compared
- **THEN** the document SHALL include a textual description of the overlap zone (e.g., "Nordbaden region, lat 47.6-49.2, lon 7.5-10.5")

### Requirement: Analyze chronological complementarity
The system SHALL compare the chronological profiles of the files.

#### Scenario: Complementarity assessment
- **WHEN** LoupBernard has precise Iron Age dates and ADAB2011 has mostly "Indéterminé"
- **THEN** the document SHALL describe how LoupBernard provides chronological precision while ADAB2011 provides volume, and quantify the difference (% of dated records per file)

### Requirement: Analyze typological complementarity
The system SHALL compare the distribution of site types across files.

#### Scenario: Type distribution comparison
- **WHEN** CARAC_LVL1 distributions are compared
- **THEN** the document SHALL include a comparison table showing the count of each type per file (e.g., LoupBernard: 90% Enceinte vs ADAB2011: 40% Habitat, 30% Funéraire)

### Requirement: Document links to existing project sources
The system SHALL identify connections between input files and other project data sources.

#### Scenario: Golden sites cross-reference
- **WHEN** `data/sources/golden_sites.csv` contains sites also present in the input files
- **THEN** the document SHALL list matching sites with the match criteria used

#### Scenario: CAG Bas-Rhin connection
- **WHEN** the CAG Bas-Rhin sub-project covers the Bas-Rhin department (adjacent to Nordbaden)
- **THEN** the document SHALL describe the potential geographic overlap for border-area sites

### Requirement: Recommend a fusion strategy
The system SHALL recommend an ordered ingestion and fusion strategy.

#### Scenario: Strategy recommendation
- **WHEN** all analyses are complete
- **THEN** the document SHALL recommend: (1) ingest LoupBernard first (higher quality), (2) ingest ADAB2011 with deduplication against LoupBernard, (3) cross-validate against golden_sites.csv, (4) enrich with CAG Bas-Rhin data for border zone

### Requirement: Provide field correspondence matrix
The system SHALL include a matrix mapping equivalent fields across all sources.

#### Scenario: Matrix content
- **WHEN** the correspondence section is generated
- **THEN** it SHALL include a table with rows for each concept (ID, name, commune, type, period, coordinates, bibliography, quality) and columns for each file plus the BaseFerRhin target schema
