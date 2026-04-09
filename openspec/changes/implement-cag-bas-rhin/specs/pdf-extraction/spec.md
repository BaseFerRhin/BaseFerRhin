## ADDED Requirements

### Requirement: Page-by-page text extraction with two-column handling

The system SHALL extract text from the CAG 67/1 PDF page by page, limiting to pages 154–660 (notices communales). For each page, the system SHALL crop the page into left half (`x0=0, x1=width/2`) and right half (`x0=width/2, x1=width`), extract text from each half separately, and concatenate left + right text.

#### Scenario: Standard two-column page extraction
- **WHEN** extracting a standard two-column page (e.g., page 200)
- **THEN** the system produces a `PageText` with page number, concatenated left+right text, detected commune header, and any inline tables

#### Scenario: Page with full-width figure
- **WHEN** a page contains a full-width figure or table that spans both columns
- **THEN** the system falls back to full-page extraction and logs a WARNING

#### Scenario: Page range enforcement
- **WHEN** the configured page range is (154, 660)
- **THEN** only pages 154 through 660 (inclusive) are processed, yielding exactly 507 page extractions

### Requirement: Commune header detection per page

The system SHALL detect the current commune from page headers matching the pattern `Commune NNN` or `Communes NNN à NNN`.

#### Scenario: Single commune header
- **WHEN** a page header contains "Commune 002"
- **THEN** the `PageText.commune_header` is set to "002"

#### Scenario: Multi-commune header
- **WHEN** a page header contains "Communes 045 à 048"
- **THEN** the `PageText.commune_header` is set to "045-048"

#### Scenario: No header detected
- **WHEN** a page has no commune header (e.g., continuation page)
- **THEN** the `PageText.commune_header` is None and the page is associated with the previous commune during splitting

### Requirement: Commune splitting from page stream

The system SHALL split the stream of `PageText` objects into `CommuneNotice` objects by detecting commune boundaries via the regex `^\d{3}\s*[-–—]\s*[A-ZÀ-Ü]`.

#### Scenario: Single-page commune
- **WHEN** commune 001 — Achenheim spans exactly one page
- **THEN** a single `CommuneNotice` is produced with `commune_id="001"`, `commune_name="Achenheim"`, and the page text

#### Scenario: Multi-page commune (Strasbourg ~50 pages)
- **WHEN** a commune spans multiple consecutive pages
- **THEN** all page texts are concatenated into a single `CommuneNotice` preserving page order

#### Scenario: Expected total communes
- **WHEN** the full extraction runs on pages 154–660
- **THEN** approximately 998 `CommuneNotice` objects are produced (±10% tolerance)

### Requirement: Sub-notice parsing within commune notices

The system SHALL split each `CommuneNotice` into `SubNotice` objects using two regex patterns: numbered entries `N* (NNN)` and lieu-dit codes `(NNN XX)`.

#### Scenario: Numbered sub-notice
- **WHEN** the commune text contains "6* (007) Dans une lœssière..."
- **THEN** a `SubNotice` is created with `sequence=6`, `code="007"`, and the text body until the next sub-notice

#### Scenario: Lieu-dit coded sub-notice
- **WHEN** the commune text contains "(003 AH) Au lieu-dit Todtenallee..."
- **THEN** a `SubNotice` is created with `code="003 AH"` and the extracted lieu-dit name

#### Scenario: Commune with no sub-notices
- **WHEN** a commune notice has no `N*` or `(NNN XX)` patterns
- **THEN** the entire commune text is treated as a single `SubNotice` with `code=None`

### Requirement: Inline metadata extraction from sub-notices

The system SHALL extract lieu-dit name, bibliographic references, and figure references from each sub-notice text.

#### Scenario: Lieu-dit extraction
- **WHEN** a sub-notice contains "Au lieu-dit Todtenallee"
- **THEN** `lieu_dit` is set to "Todtenallee"

#### Scenario: Bibliography extraction
- **WHEN** a sub-notice contains "Forrer, 1923a, p. 106"
- **THEN** the string "Forrer, 1923a, p. 106" appears in the `bibliographie` list

#### Scenario: Figure reference extraction
- **WHEN** a sub-notice contains "Fig. 28" and "Fig. 30b"
- **THEN** both "Fig. 28" and "Fig. 30b" appear in the `figures_refs` list
