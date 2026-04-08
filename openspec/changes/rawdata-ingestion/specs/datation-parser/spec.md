## ADDED Requirements

### Requirement: Unified datation parsing
The system SHALL provide a `DatationParser` that converts raw datation strings from 6 different formats into structured `PhaseOccupation`-compatible output (periode, sous_periode, datation_debut, datation_fin).

#### Scenario: Parse ArkeoGIS numeric range
- **WHEN** input is `"-620:-531"`
- **THEN** output SHALL be `[{periode: "Hallstatt", sous_periode: "Ha D", debut: -620, fin: -531}]`

#### Scenario: Parse composite text range — single period
- **WHEN** input is `"Ha C-D"`
- **THEN** output SHALL be `[{periode: "Hallstatt", sous_periode: "Ha C", debut: -800, fin: -620}, {periode: "Hallstatt", sous_periode: "Ha D", debut: -620, fin: -450}]` (2 phases)

#### Scenario: Parse composite text range — cross period
- **WHEN** input is `"Ha D3-LT A1"` or `"Ha D3-LT A"`
- **THEN** output SHALL be `[{periode: "Hallstatt", sous_periode: "Ha D3", debut: -480, fin: -450}, {periode: "La Tène", sous_periode: "LT A", debut: -450, fin: -400}]`

#### Scenario: Parse La Tène composite
- **WHEN** input is `"LT A-B"`
- **THEN** output SHALL be `[{periode: "La Tène", sous_periode: "LT A", debut: -450, fin: -380}, {periode: "La Tène", sous_periode: "LT B", debut: -380, fin: -260}]`

#### Scenario: Parse Patriarche code
- **WHEN** input is `"EURFER------"`
- **THEN** output SHALL be `[{periode: "indéterminé", sous_periode: null, debut: -800, fin: -25}]`

#### Scenario: Parse Patriarche textual datation
- **WHEN** input is `"Age du fer - Gallo-romain"`
- **THEN** output SHALL be `[{periode: "La Tène", sous_periode: null, debut: -450, fin: -25}]`

#### Scenario: Parse "Age du bronze - Age du fer"
- **WHEN** input is `"Age du bronze - Age du fer"`
- **THEN** output SHALL be `[{periode: "Hallstatt", sous_periode: null, debut: -800, fin: -450}]`

#### Scenario: Parse boolean period columns
- **WHEN** input is a dict `{"BF3_HaC": 1, "HaD": 1, "LTAB": 1, "LTCD": null}`
- **THEN** output SHALL be `[{periode: "Hallstatt", sous_periode: "Ha C"}, {periode: "Hallstatt", sous_periode: "Ha D"}, {periode: "La Tène", sous_periode: "LT A"}, {periode: "La Tène", sous_periode: "LT B"}]`

#### Scenario: Parse 14C calibrated date
- **WHEN** input is `"780-540 avant J.C"` or `"780-540"`
- **THEN** output SHALL be `[{periode: <deduced>, sous_periode: <deduced>, debut: -780, fin: -540}]`

#### Scenario: Handle indéterminé
- **WHEN** input is `"Indéterminé"` or empty
- **THEN** output SHALL be `[{periode: "indéterminé", sous_periode: null, debut: null, fin: null}]`

### Requirement: Sous-période date reference table
The system SHALL maintain a reference table mapping each sous-période to consensus date ranges.

#### Scenario: Lookup Ha D dates
- **WHEN** queried for `"Ha D"`
- **THEN** the table SHALL return `{debut: -620, fin: -450}`

#### Scenario: Lookup LT C1 dates
- **WHEN** queried for `"LT C1"`
- **THEN** the table SHALL return `{debut: -260, fin: -200}`

### Requirement: All output sous-périodes are valid
Every `sous_periode` value produced by the parser SHALL be a member of `_VALID_SUB_PERIODS` from `src/domain/models/phase.py`.

#### Scenario: No composite sous-période in output
- **WHEN** the parser processes any input format
- **THEN** no output shall contain `sous_periode` values like `"Ha C-D"`, `"LT A-B"`, or `"Ha D3-LT A1"` — these MUST be split into individual valid values
