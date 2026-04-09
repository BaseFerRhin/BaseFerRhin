## ADDED Requirements

### Requirement: Multi-page Dash application

The system SHALL provide a Dash application with 4 pages (Carte, Notices, Chronologie, Statistiques) using Dash Pages routing, dash-bootstrap-components DARKLY theme, and Inter font. The app SHALL run on port 8051.

#### Scenario: Application startup
- **WHEN** running `python -m src.ui`
- **THEN** the Dash app starts on http://localhost:8051 with the navigation bar showing all 4 page links

#### Scenario: Navigation between pages
- **WHEN** clicking "Notices" in the navigation bar
- **THEN** the Notices page content is displayed without full page reload

### Requirement: Interactive map page (carte.py)

The system SHALL display a Plotly Scattermapbox centered on the Bas-Rhin (48.6°N, 7.75°E, zoom 9) with OSM tiles. Each commune with Iron Age notices SHALL be represented as a point, sized by notice count and colored by dominant site type.

#### Scenario: Map rendering with data
- **WHEN** the Carte page loads with geocoded data in DuckDB
- **THEN** commune points are plotted on the map with hover showing commune name, notice count, and site types

#### Scenario: Commune click detail
- **WHEN** the user clicks a commune point on the map
- **THEN** a side panel displays the list of sub-notices for that commune with type and period tags

#### Scenario: Filter controls
- **WHEN** the user selects "nécropole" in the site type filter
- **THEN** only communes with at least one nécropole notice are displayed on the map

### Requirement: Notices browser page (notices.py)

The system SHALL display a two-panel layout: left panel with scrollable, filterable commune list; right panel with full notice text, highlighted keywords, bibliography, and period/vestige tags.

#### Scenario: Commune list display
- **WHEN** the Notices page loads
- **THEN** all communes are listed in the left panel with commune ID and name, total shown at bottom

#### Scenario: Text search filtering
- **WHEN** the user types "tumulus" in the search box
- **THEN** only communes whose notices contain "tumulus" are shown in the list

#### Scenario: Iron Age toggle
- **WHEN** the user enables "Fer uniquement" toggle
- **THEN** only communes with at least one Iron Age notice are displayed

#### Scenario: Notice detail display
- **WHEN** the user clicks commune "002 — Achenheim" in the list
- **THEN** the right panel shows the full notice text with Iron Age keywords highlighted and clickable period/vestige tags

### Requirement: Chronology page (chronologie.py)

The system SHALL display a horizontal bar chart showing mention counts for all periods (Néolithique through Médiéval), a detailed sub-period chart for Iron Age (Ha C, Ha D1, LT A, etc.), and a co-occurrence heatmap.

#### Scenario: Period distribution chart
- **WHEN** the Chronologie page loads
- **THEN** a bar chart displays all period mention counts from `v_stats_by_periode`

#### Scenario: Iron Age sub-periods detail
- **WHEN** the page loads
- **THEN** a separate chart shows Ha C, Ha D1, Ha D2, Ha D3, LT A, LT B, LT C, LT D counts

#### Scenario: Co-occurrence heatmap
- **WHEN** the page loads
- **THEN** a heatmap shows which normalized periods co-occur in the same notices, using data from `v_period_cooccurrence` view

### Requirement: Statistics dashboard page (stats.py)

The system SHALL display KPI cards (total communes, total notices, Iron Age notices, figure count), a donut chart of site types (including tumulus, sanctuaire as distinct types), a bar chart of top 20 communes, a treemap of vestige frequencies, and a confidence level distribution chart.

#### Scenario: KPI cards display
- **WHEN** the Stats page loads
- **THEN** 4 cards show total communes, total notices, Iron Age notices, and figure references count

#### Scenario: Top communes bar chart
- **WHEN** the Stats page loads
- **THEN** a horizontal bar chart shows the 20 communes with the most Iron Age notices

#### Scenario: Vestige treemap
- **WHEN** the Stats page loads
- **THEN** a treemap displays vestige keywords sized by frequency

#### Scenario: Confidence distribution
- **WHEN** the Stats page loads
- **THEN** a bar chart shows distribution of notices by confidence level (HIGH/MEDIUM/LOW)

### Requirement: Archaeological dark theme

The system SHALL apply a consistent dark theme: background `#0f0f1a`, surface `#16182d`, Hallstatt accent `#D95F02`, La Tène accent `#1B9E77`, gallo-romain accent `#7570B3`. Site type colors SHALL follow the defined palette: oppidum `#E31A1C`, habitat `#1F78B4`, nécropole `#6A3D9A`, tumulus `#FB9A99`, sanctuaire `#33A02C`, dépôt `#FF7F00`, atelier `#B15928`, sépulture `#CAB2D6`, indéterminé `#B2DF8A`.

#### Scenario: Theme application
- **WHEN** any page loads
- **THEN** the background is `#0f0f1a`, cards use `#16182d`, and period-specific colors match the defined palette
