## ADDED Requirements

### Requirement: Multi-criteria fuzzy deduplication
The system SHALL identify duplicate sites by computing a composite similarity score combining: site name similarity (40% weight, via `rapidfuzz.fuzz.token_sort_ratio`), commune name similarity (30% weight), and geographic proximity (30% weight, Haversine distance). Sites with a composite score above a configurable merge threshold (default: 85%) SHALL be automatically merged. Sites scoring between 70% and 85% SHALL be flagged for manual review.

#### Scenario: Automatic merge of FR/DE variants
- **WHEN** two sites exist: `nom_site="Vieux-Brisach"`, `commune="Neuf-Brisach"` and `nom_site="Breisach am Rhein"`, `commune="Breisach"`
- **THEN** the deduplicator SHALL compute a composite score above 85% and automatically merge them

#### Scenario: Flag ambiguous match for review
- **WHEN** two sites share the same commune but have different names with a composite score of 78%
- **THEN** the deduplicator SHALL flag the pair for manual review (not auto-merge)

#### Scenario: No false positive on distant homophones
- **WHEN** two sites have similar names but are >50 km apart
- **THEN** the geographic distance penalty SHALL reduce the composite score below the merge threshold

### Requirement: Merge strategy preserving all sources
When merging duplicate sites, the system SHALL retain the richest data: the site with more fields populated SHALL be the primary record. All sources from both records SHALL be preserved in the merged `sources` list. All name variants SHALL be accumulated in `variantes_nom`.

#### Scenario: Merge preserves both sources
- **WHEN** site A (from CAG 67) and site B (from Cahiers alsaciens) are merged
- **THEN** the merged site SHALL have both sources in its `sources` list

#### Scenario: Merge accumulates name variants
- **WHEN** site A has `nom_site="Münsterhügel"` and site B has `nom_site="Colline de la cathédrale"`
- **THEN** the merged site SHALL have both names: one as `nom_site` and the other in `variantes_nom`

### Requirement: Deduplication report
The system SHALL produce a deduplication report listing: total sites before, total after, number of automatic merges, number of pairs flagged for review, and details of each merge/flag decision.

#### Scenario: Report generation
- **WHEN** deduplication completes on 150 sites
- **THEN** the system SHALL write a JSON report to `data/processed/dedup_report.json` with merge statistics
