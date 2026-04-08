## ADDED Requirements

### Requirement: Multi-sheet relational extraction
The system SHALL read the 4 sheets of `Alsace_Basel_AF (1).xlsx` (`sites`, `occupations`, `mobilier`, `thésaurus`) and join them by foreign keys to produce `RawRecord` instances.

#### Scenario: Join sites with occupations
- **WHEN** sheet `sites` has a row with `id_site = 42` and sheet `occupations` has 3 rows with `fk_site = 42`
- **THEN** the extractor SHALL produce 1 `RawRecord` per site with `extra["occupations"]` containing the 3 occupation records (type, datation, commentaire)

#### Scenario: Join occupations with mobilier
- **WHEN** an occupation has `id_occupation = 7` and sheet `mobilier` has 5 rows with `fk_occupation = 7`
- **THEN** the mobilier items SHALL be stored in `extra["mobilier"]` as a list of dicts (`type_mobilier`, `NR`, `NMI`)

#### Scenario: Site without occupations
- **WHEN** a site has no matching rows in `occupations`
- **THEN** a `RawRecord` SHALL still be produced with `extra["occupations"] = []`

### Requirement: Conditional coordinate reprojection
The system SHALL reproject coordinates from the EPSG specified in `epsg_coord` to Lambert-93.

#### Scenario: WGS84 coordinates
- **WHEN** `epsg_coord = 4326` and `x = 7.58`, `y = 47.92`
- **THEN** `longitude_raw` SHALL be `7.58`, `latitude_raw` SHALL be `47.92`

#### Scenario: Already Lambert-93
- **WHEN** `epsg_coord = 2154`
- **THEN** coordinates SHALL be stored directly as L93 in `extra["x_l93"]` and `extra["y_l93"]`

### Requirement: openpyxl error workaround
The system SHALL handle the `MultiCellRange` error from openpyxl by using `pandas.read_excel()` or pre-converting the file.

#### Scenario: Read despite data validation errors
- **WHEN** `openpyxl.load_workbook()` raises a `TypeError` on data validation
- **THEN** the extractor SHALL fall back to `pandas.read_excel(engine='openpyxl')` which ignores data validations

### Requirement: Thésaurus vocabulary integration
The system SHALL read the `thésaurus` sheet to build a lookup table for type and datation normalization.

#### Scenario: Normalize occupation type via thésaurus
- **WHEN** an occupation has `type = "hab_ouv"` and the thésaurus maps `"hab_ouv"` to `"Habitat ouvert"`
- **THEN** `type_mention` SHALL be set to `"habitat"`
