## ADDED Requirements

### Requirement: Hierarchical header reconstruction
The system SHALL read the 2-level header of `BDD-fun_AFEAF24-total_04.12 (1).xlsx` sheet `PF-hallstatt` (row 0 = column groups, row 1 = sub-columns) and reconstruct flat column names.

#### Scenario: Reconstruct column names
- **WHEN** row 0 has `"info SITE"` spanning 3 columns and row 1 has `"DPT"`, `"SITE"`, `"N° ST"`
- **THEN** the reconstructed columns SHALL be `"info SITE.DPT"`, `"info SITE.SITE"`, `"info SITE.N° ST"`

#### Scenario: Handle unnamed sub-headers
- **WHEN** row 1 has `NaN` or empty values under a group header
- **THEN** the column name SHALL use only the group header name

### Requirement: AFEAF site identification
The system SHALL extract site identity from `info SITE.DPT` (département) and `info SITE.SITE` (site name) to produce `RawRecord` instances.

#### Scenario: Extract site with département
- **WHEN** `DPT = "68"` and `SITE = "Colmar rue des Aunes"`
- **THEN** `commune` SHALL be `"Colmar"`, `extra["lieu_dit"]` SHALL be `"rue des Aunes"`, `extra["departement"]` SHALL be `"68"`

#### Scenario: Extract funerary data as extra
- **WHEN** a row has monument, fosse, and mobilier columns populated
- **THEN** all funerary data SHALL be stored in `extra["funeraire"]` as a structured dict

### Requirement: AFEAF data starts at row 2
The system SHALL skip rows 0 and 1 (headers) and start data extraction at row 2.

#### Scenario: Skip header rows
- **WHEN** reading the sheet with `header=None`
- **THEN** rows 0-1 SHALL be used for header reconstruction and rows 2+ SHALL be data rows
