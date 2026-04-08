## ADDED Requirements

### Requirement: ArkeoGIS CSV extraction
The system SHALL extract archaeological site records from ArkeoGIS CSV exports (semicolon-delimited, UTF-8, WGS84) and produce `RawRecord` instances.

#### Scenario: Parse LoupBernard CSV
- **WHEN** the extractor receives `20250806_LoupBernard_ArkeoGis.csv` (116 rows, 22 columns)
- **THEN** it SHALL produce 116 `RawRecord` instances with `source_path` set to the file path, `extraction_method` set to `"arkeogis"`, and `extra["SITE_AKG_ID"]` populated

#### Scenario: Parse ADAB CSV with chronological filter
- **WHEN** the extractor receives `20250806_ADAB2011_ArkeoGis.csv` (656 rows) with `filter_age_du_fer: true`
- **THEN** it SHALL exclude rows where `STARTING_PERIOD = "Indéterminé"` and rows where `ENDING_PERIOD` contains post-Roman dates (e.g. `"1500:1699"`)
- **THEN** it SHALL log the count of excluded rows at INFO level

### Requirement: ArkeoGIS datation parsing
The system SHALL parse the ArkeoGIS date format `"START:END"` (e.g. `"-620:-531"`) into integer `datation_debut` and `datation_fin` values stored in `RawRecord.extra`.

#### Scenario: Parse standard date range
- **WHEN** `STARTING_PERIOD = "-620:-531"` and `ENDING_PERIOD = "-500:-431"`
- **THEN** `extra["datation_debut"]` SHALL be `-620` and `extra["datation_fin"]` SHALL be `-431`

#### Scenario: Handle broad date range
- **WHEN** `STARTING_PERIOD = "-800:-26"` and `ENDING_PERIOD = "-800:-26"`
- **THEN** `extra["datation_debut"]` SHALL be `-800` and `extra["datation_fin"]` SHALL be `-26`

### Requirement: ArkeoGIS type mapping
The system SHALL map `CARAC_LVL1` values to `type_mention` using the domain type vocabulary.

#### Scenario: Map known types
- **WHEN** `CARAC_LVL1 = "Enceinte"`
- **THEN** `type_mention` SHALL be `"oppidum"`

#### Scenario: Map funéraire types
- **WHEN** `CARAC_LVL1 = "Funéraire"`
- **THEN** `type_mention` SHALL be `"nécropole"`

#### Scenario: Map material categories to indéterminé
- **WHEN** `CARAC_LVL1` is `"Céramique"`, `"Métal"`, `"Lithique"`, or `"Verre"`
- **THEN** `type_mention` SHALL be `"indéterminé"` (material, not site type)

### Requirement: ArkeoGIS precision attribution
The system SHALL set `precision_localisation` based on `CITY_CENTROID` and ADAB `COMMENTS` fields.

#### Scenario: All LoupBernard are centroids
- **WHEN** `CITY_CENTROID = "Oui"` (100% of LoupBernard)
- **THEN** `extra["precision_localisation"]` SHALL be `"centroïde"`

#### Scenario: ADAB precise coordinates
- **WHEN** `CITY_CENTROID = "Non"` and `COMMENTS` contains `"GENAUIGK_T : mit 20 m Toleranz"`
- **THEN** `extra["precision_localisation"]` SHALL be `"exact"`

#### Scenario: ADAB approximate coordinates
- **WHEN** `CITY_CENTROID = "Non"` and `COMMENTS` contains `"GENAUIGK_T : mit Ungenauigkeit bis zu 200m"`
- **THEN** `extra["precision_localisation"]` SHALL be `"approx"`

### Requirement: ArkeoGIS COMMENTS parsing (ADAB)
The system SHALL extract structured German fields from the ADAB `COMMENTS` column using regex.

#### Scenario: Extract TYP_FEIN
- **WHEN** `COMMENTS` contains `"TYP_FEIN : Siedlung"`
- **THEN** `extra["TYP_FEIN"]` SHALL be `"Siedlung"`

#### Scenario: Extract DAT_FEIN
- **WHEN** `COMMENTS` contains `"DAT_FEIN : Metallzeiten"`
- **THEN** `extra["DAT_FEIN"]` SHALL be `"Metallzeiten"`

### Requirement: ArkeoGIS coordinate reprojection
The system SHALL store raw WGS84 coordinates in `latitude_raw` / `longitude_raw` and set `extra["pays"]` to `"DE"` for geocoder routing.

#### Scenario: WGS84 coordinates stored
- **WHEN** a row has `LONGITUDE = 10.083333` and `LATITUDE = 48.833332`
- **THEN** `longitude_raw` SHALL be `10.083333` and `latitude_raw` SHALL be `48.833332`
