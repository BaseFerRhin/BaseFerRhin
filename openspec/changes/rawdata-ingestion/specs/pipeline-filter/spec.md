## ADDED Requirements

### Requirement: Chronological filtering
The system SHALL provide a configurable filter that retains only records with at least one phase in the Iron Age period (-800 to -25).

#### Scenario: Retain Iron Age site
- **WHEN** a `RawRecord` has `extra["datation_debut"] = -620` and `extra["datation_fin"] = -450`
- **THEN** the record SHALL pass the filter

#### Scenario: Exclude Bronze-only site
- **WHEN** a `RawRecord` has `extra["datation_debut"] = -1200` and `extra["datation_fin"] = -800` with no Iron Age phase indicators
- **THEN** the record SHALL be excluded and logged

#### Scenario: Retain indéterminé when configured
- **WHEN** `filter_age_du_fer: false` (or not set) in the source config
- **THEN** records with `periode_mention = "Indéterminé"` SHALL pass through

#### Scenario: Exclude indéterminé when configured
- **WHEN** `filter_age_du_fer: true` in the source config
- **THEN** records with `periode_mention = "Indéterminé"` and no other Iron Age evidence SHALL be excluded

### Requirement: Geographic filtering
The system SHALL provide a configurable filter by department or country.

#### Scenario: Filter by department list
- **WHEN** `filter_departments: [67, 68]` is configured
- **THEN** only records with `extra["departement"]` IN `[67, 68]` or `commune` within those departments SHALL pass

#### Scenario: Filter by perimeter
- **WHEN** `filter_perimeter: true` is configured
- **THEN** records outside the Rhin supérieur perimeter (Alsace 67/68 + Bade-Wurtemberg + Bâle) SHALL be excluded based on `extra["pays"]` and `extra["departement"]`

### Requirement: Exclusion logging
The system SHALL log all filtered-out records with their source, reason for exclusion, and key identifiers.

#### Scenario: Log exclusion details
- **WHEN** a record is excluded by the chronological filter
- **THEN** a log entry at INFO level SHALL include: `source_path`, `commune`, `periode_mention`, and `"reason: hors périmètre chronologique"`

#### Scenario: Exclusion summary at end
- **WHEN** filtering is complete for a source
- **THEN** a summary log SHALL report: `"Source X: Y/Z records retained, W excluded (chrono: A, geo: B)"`
