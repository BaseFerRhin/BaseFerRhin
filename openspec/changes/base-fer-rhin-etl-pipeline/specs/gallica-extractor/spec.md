## ADDED Requirements

### Requirement: SRU search for archaeological documents
The system SHALL query the Gallica SRU API (`/services/engine/search/sru?operation=searchRetrieve&version=1.2`) using CQL queries to discover documents matching archaeological keywords (e.g., `notice all "carte archéologique de la Gaule" and dc.subject all "bas-rhin"`). The extractor SHALL parse the XML response to extract ARK identifiers, titles, authors, and publication dates.

#### Scenario: Discover CAG Bas-Rhin via SRU
- **WHEN** a SRU search is executed with query `notice all "carte archéologique de la Gaule" and dc.subject all "bas-rhin"`
- **THEN** the system SHALL return at least one result containing ARK `ark:/12148/bd6t542071728`

#### Scenario: Discover CAG Haut-Rhin via SRU
- **WHEN** a SRU search is executed with query `notice all "carte archéologique de la Gaule Haut-Rhin"`
- **THEN** the system SHALL return at least one result with a valid ARK identifier for the CAG 68 volume

#### Scenario: SRU pagination
- **WHEN** a SRU query returns more than 15 results
- **THEN** the system SHALL paginate using `startRecord` and `maximumRecords` parameters until all results are collected

### Requirement: OCR text extraction per page
The system SHALL download raw OCR text for any Gallica page via the endpoint `https://gallica.bnf.fr/ark:/{ark_id}/f{page}.texteBrut`. The extractor SHALL handle HTTP errors (404, 500) with retry logic and return the raw text content.

#### Scenario: Extract text from CAG 67 page
- **WHEN** the extractor fetches OCR text for `ark:/12148/bd6t542071728` page 50
- **THEN** the system SHALL return a non-empty string containing the OCR text of that page

#### Scenario: Handle missing page gracefully
- **WHEN** the extractor fetches OCR text for a page number exceeding the document's total pages
- **THEN** the system SHALL return `None` and log a warning (not raise an exception)

### Requirement: OCR quality scoring
The system SHALL compute an OCR confidence score (0.0–1.0) for each extracted page based on the ratio of recognized dictionary words to total word count. A configurable threshold (default: 0.4) SHALL determine whether a page is marked as readable or flagged for manual review.

#### Scenario: High quality OCR page
- **WHEN** a page has 85% recognized words
- **THEN** the OCR confidence score SHALL be 0.85 and the page SHALL be marked as readable

#### Scenario: Low quality OCR page
- **WHEN** a page has 30% recognized words
- **THEN** the OCR confidence score SHALL be 0.30 and the page SHALL be flagged for manual review

### Requirement: ALTO XML structured extraction
The system SHALL download ALTO XML for any Gallica page via `/RequestDigitalElement?O={ark_id}&E=ALTO&Deb={page}`. The extractor SHALL parse the XML to extract text blocks with spatial coordinates (bounding boxes).

#### Scenario: Extract ALTO with coordinates
- **WHEN** ALTO XML is fetched for a page containing a table of archaeological sites
- **THEN** the system SHALL return a list of text blocks, each with `text`, `x`, `y`, `width`, `height` attributes

### Requirement: IIIF image retrieval for maps and plates
The system SHALL download images via the IIIF Image API (`/iiif/ark:/{ark_id}/f{page}/full/max/0/default.jpg`) for pages identified as containing maps or archaeological plates.

#### Scenario: Download a map image
- **WHEN** the extractor fetches the IIIF image for a page identified as a map
- **THEN** the system SHALL save the image to `data/raw/gallica/{ark_id}/f{page}.jpg`

### Requirement: Rate limiting and caching
The system SHALL limit concurrent requests to Gallica APIs to a maximum of 5 simultaneous connections. All downloaded pages (OCR text, ALTO XML, images) SHALL be cached locally in `data/raw/gallica/` to avoid redundant downloads on subsequent pipeline runs.

#### Scenario: Cache hit avoids re-download
- **WHEN** the extractor is asked to fetch a page that was already downloaded and cached
- **THEN** the system SHALL return the cached content without making an HTTP request

#### Scenario: Concurrent request throttling
- **WHEN** the pipeline triggers 20 simultaneous page downloads
- **THEN** at most 5 HTTP requests SHALL be active at any given time

### Requirement: Archaeological site mention extraction
The system SHALL extract mentions of archaeological sites from OCR text using regex patterns matching commune names followed by site descriptors (e.g., "Strasbourg — habitat hallstattien", "tumulus de Haguenau"). Each extraction SHALL produce a raw record with `commune`, `type_mention`, `context_text`, `page_number`, `ark_id`.

#### Scenario: Extract site mention from CAG text
- **WHEN** OCR text contains "BRUMATH [...] Habitat de l'époque de Hallstatt repéré en prospection"
- **THEN** the system SHALL extract a record with `commune="Brumath"`, `type_mention="habitat"`, `context_text` containing the surrounding paragraph
