## ADDED Requirements

### Requirement: Generate analysis markdown document per file
The system SHALL produce an `analysis.md` document in `data/analysis/<file_stem>/` that provides a comprehensive human-readable analysis of the input file.

#### Scenario: Document structure
- **WHEN** analysis.md is generated
- **THEN** it SHALL contain the sections: Vue d'ensemble, Schéma détaillé des colonnes, Analyse du modèle de données, Analyse de qualité, Mapping vers le modèle BaseFerRhin, Stratégie d'ingestion, Limites et précautions

### Requirement: Analysis SHALL document column schema
The system SHALL document each column with its type, description, fill rate, and top values.

#### Scenario: Column documentation for categorical columns
- **WHEN** a column has fewer than 50 distinct values
- **THEN** the analysis SHALL list the top 10 values with their counts

#### Scenario: Column documentation for numeric columns
- **WHEN** a column is numeric (LONGITUDE, LATITUDE, ALTITUDE)
- **THEN** the analysis SHALL include min, max, mean, and standard deviation

### Requirement: Analysis SHALL explain the ArkeoGIS multi-row model
The system SHALL clearly explain how a single archaeological site maps to multiple rows in ArkeoGIS format.

#### Scenario: Multi-row explanation
- **WHEN** the analysis documents the data model
- **THEN** it SHALL include the CARAC_* hierarchy tree (CARAC_NAME → LVL1 → LVL2 → LVL3 → LVL4) with observed values, and the ratio of total rows to unique sites

### Requirement: Analysis SHALL define the mapping to BaseFerRhin model
The system SHALL provide an explicit field-by-field mapping table from ArkeoGIS columns to BaseFerRhin normalized fields.

#### Scenario: Mapping table
- **WHEN** the mapping section is generated
- **THEN** it SHALL contain a table with columns: Champ ArkeoGIS, Champ BaseFerRhin, Transformation — covering at minimum: SITE_NAME, MAIN_CITY_NAME, LONGITUDE/LATITUDE, STARTING/ENDING_PERIOD, CARAC_LVL1, STATE_OF_KNOWLEDGE, BIBLIOGRAPHY, COMMENTS

#### Scenario: Mapping references existing project files
- **WHEN** the mapping involves type classification or period assignment
- **THEN** it SHALL reference the specific project reference files (`types_sites.json`, `periodes.json`, `toponymes_fr_de.json`)

### Requirement: Analysis SHALL detail a 6-step ingestion strategy
The system SHALL describe a concrete ingestion pipeline in 6 steps.

#### Scenario: Ingestion steps
- **WHEN** the strategy section is generated
- **THEN** it SHALL cover: (1) Chargement CSV, (2) Nettoyage encodage/valeurs, (3) Agrégation multi-lignes → sites, (4) Classification type/période/confiance, (5) Géocodage/projection, (6) Export RawRecord

### Requirement: Analysis SHALL document data quality issues
The system SHALL identify and document all quality issues specific to the file.

#### Scenario: Quality section content
- **WHEN** quality issues are documented
- **THEN** the section SHALL cover: taux de valeurs manquantes par colonne, coordonnées aberrantes, doublons potentiels, problèmes d'encodage, et biais des centroïdes communaux
