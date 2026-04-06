## ADDED Requirements

### Requirement: Site type normalization FR/DE
The system SHALL normalize site type mentions from free text (FR and DE) to the canonical `TypeSite` enum. The normalizer SHALL use a lookup dictionary mapping known aliases to standard codes (e.g., "fortification" → OPPIDUM, "Höhensiedlung" → OPPIDUM, "Gräberfeld" → NECROPOLE, "cimetière" → NECROPOLE). Matching SHALL be case-insensitive.

#### Scenario: French alias normalization
- **WHEN** raw text contains "fortification de hauteur"
- **THEN** the normalizer SHALL return `TypeSite.OPPIDUM`

#### Scenario: German alias normalization
- **WHEN** raw text contains "Höhensiedlung"
- **THEN** the normalizer SHALL return `TypeSite.OPPIDUM`

#### Scenario: Unknown type fallback
- **WHEN** raw text contains an unrecognized site type "Bodenmarkierung"
- **THEN** the normalizer SHALL return `TypeSite.INDETERMINE` and log the unrecognized term

### Requirement: Period normalization with sub-periods
The system SHALL normalize period mentions to the canonical `Periode` enum and extract sub-periods when present. The normalizer SHALL recognize patterns like "Hallstatt D", "Ha D1", "LT B2", "La Tène ancienne", "premier âge du Fer", "Frühlatènezeit", "Spätlatènezeit".

#### Scenario: Full period text normalization
- **WHEN** raw text contains "premier âge du Fer"
- **THEN** the normalizer SHALL return `Periode.HALLSTATT` with `sous_periode=None`

#### Scenario: Sub-period extraction
- **WHEN** raw text contains "Ha D2-D3"
- **THEN** the normalizer SHALL return `Periode.HALLSTATT` with `sous_periode="Ha D2-D3"`

#### Scenario: German period normalization
- **WHEN** raw text contains "Spätlatènezeit"
- **THEN** the normalizer SHALL return `Periode.LA_TENE` with `sous_periode="LT D"`

### Requirement: Toponym concordance FR/DE
The system SHALL maintain a bilingual concordance dictionary mapping current French commune names to their historical German equivalents and vice versa. The normalizer SHALL resolve any toponym variant to its canonical current form.

#### Scenario: German to French resolution
- **WHEN** a source references "Schlettstadt"
- **THEN** the normalizer SHALL resolve to canonical commune "Sélestat"

#### Scenario: Historical name resolution
- **WHEN** a source references "Brocomagus"
- **THEN** the normalizer SHALL resolve to canonical commune "Brumath" and store "Brocomagus" in `variantes_nom`

#### Scenario: Already canonical name
- **WHEN** a source references "Strasbourg"
- **THEN** the normalizer SHALL return "Strasbourg" unchanged

### Requirement: Composite normalization pipeline
The system SHALL apply type, period, and toponym normalization in sequence to transform a `RawRecord` into a partially populated `Site` model. Unresolvable fields SHALL be left as `None` with a quality comment.

#### Scenario: Full normalization of a CAG entry
- **WHEN** a RawRecord has `commune="Zabern"`, `type_mention="Höhensiedlung"`, `periode_mention="Hallstatt D"`
- **THEN** the normalized output SHALL have `commune="Saverne"`, `type_site=OPPIDUM`, `periode=HALLSTATT`, `sous_periode="Ha D"`, and `variantes_nom=["Zabern"]`
