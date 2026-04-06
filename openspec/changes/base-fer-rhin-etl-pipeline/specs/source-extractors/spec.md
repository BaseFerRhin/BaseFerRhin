## ADDED Requirements

### Requirement: Common extractor interface
The system SHALL define an abstract `SourceExtractor` protocol with methods: `extract(source_path: Path) -> list[RawRecord]` and `supported_formats() -> list[str]`. All extractors (Gallica, PDF, CSV) SHALL implement this interface.

#### Scenario: Extractor dispatch by file type
- **WHEN** a PDF file is provided to the pipeline
- **THEN** the system SHALL dispatch to the PDF extractor based on file extension

#### Scenario: Unsupported format rejection
- **WHEN** a `.docx` file is provided
- **THEN** the system SHALL raise a `UnsupportedFormatError` with the file extension

### Requirement: PDF extractor via pdfplumber
The system SHALL extract text from local PDF files using `pdfplumber`. For each page, the extractor SHALL produce raw text and detect tables. Table rows SHALL be returned as structured records.

#### Scenario: Extract text from archaeological report PDF
- **WHEN** a PDF containing site inventory tables is processed
- **THEN** the system SHALL return raw text per page and structured table rows with column headers

#### Scenario: Handle scanned PDF without text layer
- **WHEN** a PDF page has no extractable text (image-only)
- **THEN** the system SHALL flag the page as `needs_ocr=True` and return empty text

### Requirement: CSV extractor with column mapping
The system SHALL read CSV and Excel files and map columns to the domain model fields via a configurable column mapping dictionary. The extractor SHALL handle common encodings (UTF-8, Latin-1, CP1252) and delimiters (comma, semicolon, tab).

#### Scenario: Import CSV with semicolon delimiter
- **WHEN** a CSV file with semicolon delimiters and Latin-1 encoding is provided
- **THEN** the system SHALL correctly parse all rows and map columns to RawRecord fields

#### Scenario: Column mapping configuration
- **WHEN** a CSV has columns `Nom`, `Gemeinde`, `Typ`, `Lat`, `Lon`
- **THEN** the system SHALL map them to `nom_site`, `commune`, `type_site`, `latitude`, `longitude` using the provided mapping dict

### Requirement: RawRecord intermediate format
The system SHALL define a `RawRecord` dataclass as the common intermediate format between extraction and normalization. Fields SHALL include: `raw_text`, `commune`, `type_mention`, `periode_mention`, `latitude_raw`, `longitude_raw`, `source_path`, `page_number`, `extraction_method`.

#### Scenario: RawRecord from Gallica OCR
- **WHEN** the Gallica extractor produces output
- **THEN** it SHALL be a list of RawRecord instances with `extraction_method="gallica_ocr"`

#### Scenario: RawRecord from CSV
- **WHEN** the CSV extractor produces output
- **THEN** it SHALL be a list of RawRecord instances with `extraction_method="csv"` and structured field values
