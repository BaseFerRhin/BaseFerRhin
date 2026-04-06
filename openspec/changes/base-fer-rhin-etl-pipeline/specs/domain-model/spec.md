## ADDED Requirements

### Requirement: Site aggregate with Pydantic validation
The system SHALL define a `Site` Pydantic BaseModel as the root aggregate with mandatory fields: `site_id` (prefixed string, PK), `nom_site` (str), `commune` (str), `pays` (enum FR/DE/CH), `precision_localisation` (enum), and `type_site` (enum). Optional fields SHALL include `latitude`, `longitude`, `surface_m2`, `altitude_m`, `description`, `statut_fouille`, `identifiants_externes`, `commentaire_qualite`. The `site_id` SHALL be prefixed by source (e.g., `CAG67-STRASBOURG-042`).

#### Scenario: Valid site creation
- **WHEN** a Site is instantiated with all required fields and valid enums
- **THEN** the model SHALL validate successfully and serialize to JSON

#### Scenario: Missing required field rejection
- **WHEN** a Site is instantiated without `commune`
- **THEN** a `ValidationError` SHALL be raised with a message indicating the missing field

#### Scenario: Invalid enum rejection
- **WHEN** a Site is instantiated with `pays="IT"`
- **THEN** a `ValidationError` SHALL be raised because "IT" is not in the allowed enum (FR, DE, CH)

### Requirement: Multi-phase occupation model
The system SHALL define a `PhaseOccupation` model linked to Site via `site_id`. Each phase SHALL have a required `periode` enum (HALLSTATT, LA_TENE, TRANSITION, INDETERMINE) and optional fields: `sous_periode`, `datation_debut` (negative int for BCE), `datation_fin`, `methode_datation`, `mobilier_associe` (list of strings).

#### Scenario: Site with multiple occupation phases
- **WHEN** a Site is created with two PhaseOccupation entries (Hallstatt D and La Tène A)
- **THEN** both phases SHALL be stored in the `phases` list and each SHALL validate independently

#### Scenario: Chronological sub-period validation
- **WHEN** a PhaseOccupation has `periode=HALLSTATT` and `sous_periode="LT B2"`
- **THEN** the validator SHALL flag an inconsistency (La Tène sub-period under Hallstatt period)

### Requirement: Multi-source tracking per site
The system SHALL define a `Source` model linked to Site via `site_id`. Each source SHALL have required fields: `reference` (str) and `niveau_confiance` (enum: élevé/moyen/faible). Optional fields SHALL include `type_source` (enum), `url`, `ark_gallica`, `page_gallica`, `confiance_ocr` (float 0.0–1.0), `date_extraction`.

#### Scenario: Site from multiple Gallica sources
- **WHEN** a Site has one Source from CAG 67 and another from Cahiers alsaciens
- **THEN** both sources SHALL be stored in the `sources` list with distinct `source_id` values

#### Scenario: Gallica-specific fields
- **WHEN** a Source has `type_source="gallica_cag"` and `ark_gallica="ark:/12148/bd6t542071728"`
- **THEN** the source SHALL accept `page_gallica` and `confiance_ocr` fields

### Requirement: TypeSite normalized enum
The system SHALL define a `TypeSite` enum with values: OPPIDUM, HABITAT, NECROPOLE, DEPOT, SANCTUAIRE, ATELIER, VOIE, TUMULUS, INDETERMINE.

#### Scenario: All standard types accepted
- **WHEN** iterating through all 9 TypeSite enum values
- **THEN** each SHALL be a valid enum member with a string value

### Requirement: Periode normalized enum
The system SHALL define a `Periode` enum with values: HALLSTATT, LA_TENE, TRANSITION, INDETERMINE.

#### Scenario: Period enum serialization
- **WHEN** a Periode.HALLSTATT is serialized to JSON
- **THEN** the output SHALL be the string `"Hallstatt"`

### Requirement: Automatic timestamps
The system SHALL automatically set `date_creation` on first instantiation and `date_maj` on every update for Site, PhaseOccupation, and Source models.

#### Scenario: Creation timestamp
- **WHEN** a new Site is created without specifying `date_creation`
- **THEN** `date_creation` SHALL be set to the current UTC datetime

#### Scenario: Update timestamp
- **WHEN** a Site's `description` field is modified
- **THEN** `date_maj` SHALL be updated to the current UTC datetime
