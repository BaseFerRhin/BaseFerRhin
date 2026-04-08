## ADDED Requirements

### Requirement: CAG DOC OLE2 text extraction
The system SHALL extract text from `.doc` OLE2 files using `antiword` CLI subprocess.

#### Scenario: Extract CAG 68 text
- **WHEN** the extractor receives `cag_68_texte.doc` (1.4 MB, OLE2 format)
- **THEN** it SHALL execute `antiword <path>` and capture stdout as UTF-8 text

#### Scenario: antiword not installed
- **WHEN** `antiword` is not found in PATH
- **THEN** the extractor SHALL raise a clear error: `"antiword is required for .doc OLE2 files. Install with: brew install antiword"`

#### Scenario: Extract CAG 68 index
- **WHEN** the extractor receives `cag_68_index.doc`
- **THEN** it SHALL extract the commune index for cross-referencing with notices

### Requirement: CAG notice parsing
The system SHALL parse CAG text into individual site notices, each producing a `RawRecord`.

#### Scenario: Parse commune-level notice
- **WHEN** text contains a notice block starting with a commune number and name (e.g. `"150 — GEISPOLSHEIM"`)
- **THEN** a `RawRecord` SHALL be produced with `commune = "GEISPOLSHEIM"` and `extra["cag_commune_id"] = "150"`

#### Scenario: Parse lieu-dit sub-notice
- **WHEN** a commune notice contains sub-entries by lieu-dit with vestiges and datation
- **THEN** each sub-entry SHALL produce a separate `RawRecord` with `extra["lieu_dit"]` populated

#### Scenario: Extract bibliography references
- **WHEN** a notice contains bibliographic references
- **THEN** they SHALL be stored in `extra["bibliographie"]`

### Requirement: CAG PDF OCR extraction
The system SHALL extract text from the PDF scan `CAG Bas-Rhin.pdf` (209 MB) using the existing Tesseract OCR pipeline.

#### Scenario: Process PDF by pages
- **WHEN** the extractor receives the 209 MB PDF
- **THEN** it SHALL split the PDF into pages and OCR each page individually to manage memory

#### Scenario: Apply same notice parsing
- **WHEN** OCR text is produced for a page
- **THEN** the same notice parser from the DOC extractor SHALL be reused

#### Scenario: Log OCR confidence
- **WHEN** Tesseract produces an OCR result for a page
- **THEN** the confidence score SHALL be stored in `extra["ocr_confidence"]`
