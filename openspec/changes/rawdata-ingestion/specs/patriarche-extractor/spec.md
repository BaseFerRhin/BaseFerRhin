## ADDED Requirements

### Requirement: Patriarche XLSX extraction
The system SHALL extract archaeological records from `20250806_Patriarche_ageFer.xlsx` (836 rows, 5 columns) via multi-strategy parsing of the `Identification_de_l_EA` field.

#### Scenario: Parse standard 6-slash format
- **WHEN** `Identification_de_l_EA` = `"8342 / 67 019 0009 / BALDENHEIM /  / SCHLITTWEG / habitat / Age du fer - Gallo-romain"`
- **THEN** the extractor SHALL produce a `RawRecord` with `commune = "BALDENHEIM"`, `type_mention = "habitat"`, `periode_mention = "Age du fer - Gallo-romain"`, `extra["lieu_dit"] = "SCHLITTWEG"`, `extra["patriarche_ea"] = "67 019 0009"`

#### Scenario: Parse reversed order (type before datation)
- **WHEN** `Identification_de_l_EA` = `"10901 / 67 008 0013 / ALTORF /  / Birckenwald / tumulus / Age du bronze - Age du fer"`
- **THEN** the extractor SHALL classify `"tumulus"` as `type_mention` and `"Age du bronze - Age du fer"` as `periode_mention` using heuristic detection (datation keywords: "Age", "Hallstatt", "Fer", "Gallo", "Bronze", "Tène")

#### Scenario: Parse 5-slash format (missing field)
- **WHEN** `Identification_de_l_EA` has only 5 slashs (e.g. `"12163 / 67 008 0022 / ALTORF /  / Osterlaeng / Age du fer"`)
- **THEN** the extractor SHALL extract available fields and set missing ones to `null`

#### Scenario: Parse 7-slash format
- **WHEN** `Identification_de_l_EA` has 7 slashs (32 occurrences)
- **THEN** the extractor SHALL handle the extra field by classifying each segment via heuristics

### Requirement: Patriarche EA cross-reference
The system SHALL populate `extra["patriarche_ea"]` with `Numero_de_l_EA` and `extra["patriarche_code_national"]` with `Code_national_de_l_EA`.

#### Scenario: EA identifier stored for deduplication
- **WHEN** `Numero_de_l_EA = "67 001 0006"` and `Code_national_de_l_EA = 11121`
- **THEN** `extra["patriarche_ea"]` SHALL be `"67 001 0006"` and `extra["patriarche_code_national"]` SHALL be `"11121"`

### Requirement: Patriarche-DBF coordinate enrichment
The system SHALL cross-reference Patriarche EA codes with `ea_fr.dbf` to recover WGS84 coordinates.

#### Scenario: Match by EA code
- **WHEN** `extra["patriarche_ea"]` matches `EA_NATCODE` in `ea_fr.dbf`
- **THEN** `latitude_raw` and `longitude_raw` SHALL be populated from `Y_DEGRE` and `X_DEGRE`

#### Scenario: No match found
- **WHEN** no `EA_NATCODE` matches in `ea_fr.dbf`
- **THEN** coordinates SHALL remain `null` (geocoding by commune downstream)
