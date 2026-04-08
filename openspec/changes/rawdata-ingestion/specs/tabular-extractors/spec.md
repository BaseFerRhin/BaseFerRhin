## ADDED Requirements

### Requirement: DBF file extraction
The system SHALL extract records from `.dbf` files using `dbfread` with Latin-1 encoding.

#### Scenario: Extract ea_fr.dbf
- **WHEN** the extractor receives `ea_fr.dbf` (42 records, 31 fields)
- **THEN** it SHALL produce 42 `RawRecord` instances with `commune` from `COMMUNE_PP`, `longitude_raw` from `X_DEGRE`, `latitude_raw` from `Y_DEGRE`, `type_mention` from `VESTIGES`, `periode_mention` from `CHRONO_DEB`/`CHRONO_FIN`

#### Scenario: Decode Patriarche chronology codes
- **WHEN** `CHRONO_DEB = "EURFER------"` and `CHRONO_FIN = "EURFER------"`
- **THEN** `periode_mention` SHALL be `"âge du Fer"` and `extra["chrono_code_deb"]` SHALL be `"EURFER------"`

#### Scenario: Handle afeaf_lineaire.dbf with generic column names
- **WHEN** the extractor receives `2026_afeaf_lineaire.dbf` (9 fields: `id, a, b, c, d, e, f, g, h`)
- **THEN** it SHALL store all fields in `extra` with original names and set `extraction_method = "dbf"`

### Requirement: ODS file extraction
The system SHALL extract records from `.ods` files using `pandas` with `odfpy` engine.

#### Scenario: Extract mobilier_sepult_def.ods
- **WHEN** the extractor receives `20240425_mobilier_sepult_def (1).ods`
- **THEN** it SHALL produce `RawRecord` instances with all columns stored in `extra` (enrichment source, not primary)

### Requirement: BdD Proto Alsace Bronze age filtering
The system SHALL filter `BdD_Proto_Alsace (1).xlsx` to retain only rows with at least one Iron Age phase.

#### Scenario: Retain row with HaD phase
- **WHEN** a row has `HaD = 1.0` and all other period columns null
- **THEN** the row SHALL be retained and produce a `RawRecord`

#### Scenario: Exclude Bronze-only row
- **WHEN** a row has `BF1 = 1.0`, `BF2 = 1.0` but `BF3_HaC`, `HaD`, `LTAB`, `LTCD` are all null
- **THEN** the row SHALL be excluded and logged

#### Scenario: Parse boolean period columns into phases
- **WHEN** a row has `BF3_HaC = 1.0` and `LTAB = 1.0`
- **THEN** `extra["phases_bool"]` SHALL contain `["BF3_HaC", "LTAB"]`

### Requirement: Inhumations silos site aggregation
The system SHALL aggregate individual-level rows from `Inhumations silos` into site-level `RawRecord` instances.

#### Scenario: Aggregate individuals into sites
- **WHEN** 5 rows share `Site = "Bergheim"` and `Lieu dit = "Saulager"`
- **THEN** 1 `RawRecord` SHALL be produced with `commune = "Bergheim"`, `extra["lieu_dit"] = "Saulager"`, `extra["individus_count"] = 5`

#### Scenario: Filter parasitic rows
- **WHEN** `Département` contains `"TOTAL"`, `"Supprimé"`, or `"Département"`
- **THEN** the row SHALL be excluded

#### Scenario: Parse 14C calibrated dates
- **WHEN** `14C (2 sigma)` = `"780-540 avant J.C"`
- **THEN** `extra["datation_14c_debut"]` SHALL be `-780` and `extra["datation_14c_fin"]` SHALL be `-540`

### Requirement: Habitats-tombes riches normalization
The system SHALL normalize and filter `habitats-tombes riches` data.

#### Scenario: Normalize pays casing
- **WHEN** `Pays = "f"`
- **THEN** `extra["pays"]` SHALL be `"FR"`

#### Scenario: Filter parasitic Dept/Land values
- **WHEN** `Dept/Land` contains `"Manque Tombes de"` or similar non-geographic values
- **THEN** the row SHALL be excluded and logged

#### Scenario: Map rich tomb types
- **WHEN** `type = "tombe princière ?"`
- **THEN** `type_mention` SHALL be `"nécropole"`

#### Scenario: Map fortified height site
- **WHEN** `type = "site fortifié de hauteur"`
- **THEN** `type_mention` SHALL be `"oppidum"`

### Requirement: Necropoles geographic filtering
The system SHALL filter `necropoles_BFIIIb-HaD3` to retain only Alsace departments when configured.

#### Scenario: Filter to Alsace
- **WHEN** `filter_departments: [67, 68]` is configured
- **THEN** only rows with `Dept IN (67, 68)` SHALL be retained (200 of 339)

#### Scenario: No filter configured
- **WHEN** `filter_departments` is not set
- **THEN** all 339 rows SHALL be retained
