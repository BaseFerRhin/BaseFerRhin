## ADDED Requirements

### Requirement: Iron Age keyword filtering

The system SHALL filter sub-notices by matching against a regex of Iron Age keywords including: hallstatt, la tène, âge du fer, protohistor, tumulus, tertre funéraire, Ha A-D (all sub-periods), LT A-D (all sub-periods), LT finale, premier/second âge du fer, âge du bronze final, BF IIIa/b, eisenzeit, latènezeit, and German terms: Grabhügel, Hügelgrab, Flachgrab, Ringwall, Viereckschanze, Fürstengrab, Fürstensitz.

#### Scenario: Sub-notice with Hallstatt mention
- **WHEN** a sub-notice text contains "époque de Hallstatt"
- **THEN** `has_iron_age` is True and "Hallstatt" appears in `periode_mentions`

#### Scenario: Sub-notice with La Tène sub-period
- **WHEN** a sub-notice text contains "LT D1"
- **THEN** `has_iron_age` is True and "La Tène" appears in `periode_mentions`

#### Scenario: Purely Gallo-Roman sub-notice
- **WHEN** a sub-notice text mentions only "gallo-romain" with no Iron Age keywords
- **THEN** `has_iron_age` is False

#### Scenario: Mixed-period sub-notice
- **WHEN** a sub-notice mentions both "Hallstatt" and "gallo-romain"
- **THEN** `has_iron_age` is True and `all_periods` contains both periods

### Requirement: Vestige type classification

The system SHALL classify each sub-notice by site type using keyword matching against French and German terms: tumulus, tertre, sépulture, nécropole, habitat, oppidum, fortification, enceinte, silo, fosse, four, atelier, dépôt, tombe, inhumation, incinération, urne, céramique, tessons, fibule, bracelet, épée, monnaie, torque, hache, rasoir, poignard, anneau, poterie, sanctuaire, fanum, lieu de culte, Viereckschanze, Grabhügel, Hügelgrab, Flachgrab, Ringwall, Siedlung, Brandgrab, Fürstengrab. The type hierarchy SHALL distinguish: oppidum > sanctuaire > nécropole > tumulus > sépulture > habitat > atelier > dépôt > indéterminé.

#### Scenario: Necropolis vs tumulus distinction
- **WHEN** a sub-notice text contains "nécropole" (formal cemetery)
- **THEN** `type_site` is "nécropole"

#### Scenario: Isolated tumulus
- **WHEN** a sub-notice text contains "tumulus" or "Grabhügel" but NOT "nécropole"
- **THEN** `type_site` is "tumulus" (distinct from nécropole)

#### Scenario: Sanctuaire detection
- **WHEN** a sub-notice text contains "sanctuaire", "fanum", or "Viereckschanze"
- **THEN** `type_site` is "sanctuaire"

#### Scenario: No vestige keywords
- **WHEN** a sub-notice text contains no known vestige keywords
- **THEN** `type_site` is "indéterminé" and `vestiges_mentions` is empty

### Requirement: SiteRecord construction

The system SHALL build a `SiteRecord` dataclass for each filtered sub-notice containing: commune_id, commune_name, sous_notice_code, lieu_dit, type_site, periode_mentions, vestiges_mentions, raw_text (truncated 500 chars), full_text, page_number, bibliographie, figures_refs, has_iron_age, all_periods, confidence_level (HIGH/MEDIUM/LOW).

#### Scenario: Complete SiteRecord
- **WHEN** a sub-notice from commune 002 — Achenheim, code 007, mentions Hallstatt and tumulus
- **THEN** a SiteRecord is built with `commune_id="002"`, `commune_name="Achenheim"`, `sous_notice_code="007"`, `has_iron_age=True`, `type_site="tumulus"`, `periode_mentions=["Hallstatt"]`

#### Scenario: Raw text truncation
- **WHEN** the sub-notice full text exceeds 500 characters
- **THEN** `raw_text` contains the first 500 characters and `full_text` contains the complete text

#### Scenario: Confidence level estimation
- **WHEN** a sub-notice references recent excavation ("fouille") with post-1980 bibliography
- **THEN** `confidence_level` is "HIGH"

#### Scenario: Low confidence for old isolated finds
- **WHEN** a sub-notice has no figures, only pre-1950 bibliography, and no excavation mention
- **THEN** `confidence_level` is "LOW"
