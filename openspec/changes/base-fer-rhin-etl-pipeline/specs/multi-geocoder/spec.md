## ADDED Requirements

### Requirement: Country-adaptive geocoding dispatch
The system SHALL dispatch geocoding requests to the appropriate API based on the site's `pays` field: Nominatim/BAN for `FR`, BKG/Nominatim for `DE`, geo.admin.ch/Nominatim for `CH`. Each geocoder SHALL implement a common `Geocoder` protocol with method `geocode(commune: str, site_name: str | None, pays: str) -> GeoResult | None`.

#### Scenario: French site geocoded via BAN
- **WHEN** a site has `pays="FR"` and `commune="Brumath"`
- **THEN** the system SHALL query the BAN API first and return coordinates within Brumath territory

#### Scenario: German site geocoded via Nominatim
- **WHEN** a site has `pays="DE"` and `commune="Breisach am Rhein"`
- **THEN** the system SHALL query Nominatim with country restriction `countrycodes=de`

#### Scenario: Swiss site geocoded via geo.admin.ch
- **WHEN** a site has `pays="CH"` and `commune="Basel"`
- **THEN** the system SHALL query the geo.admin.ch search API and return coordinates

### Requirement: Fallback chain with degradation tracking
If the primary geocoder returns no result, the system SHALL fallback to Nominatim (generic). If all geocoders fail, the system SHALL use the commune centroid from a local reference table and set `precision_localisation="centroide"`.

#### Scenario: Primary geocoder fails, Nominatim succeeds
- **WHEN** BAN returns no result for a French lieu-dit but Nominatim finds it
- **THEN** the system SHALL use Nominatim coordinates and log the fallback

#### Scenario: All geocoders fail, centroid used
- **WHEN** no geocoder finds coordinates for "Hohlandsbourg" in commune "Wintzenheim"
- **THEN** the system SHALL use the centroid of Wintzenheim and set `precision_localisation="centroide"`

#### Scenario: Complete failure logged for manual review
- **WHEN** no geocoder succeeds and no commune centroid is available
- **THEN** the site SHALL be added to the manual review queue with `latitude=None`, `longitude=None`

### Requirement: Rate limiting per geocoding API
The system SHALL enforce per-API rate limits: Nominatim (1 req/s as per usage policy), BAN (50 req/s), geo.admin.ch (10 req/s). A local cache SHALL store previously geocoded communes to minimize API calls.

#### Scenario: Nominatim rate compliance
- **WHEN** 10 geocoding requests target Nominatim in sequence
- **THEN** the requests SHALL be spaced at least 1 second apart

#### Scenario: Cache hit avoids API call
- **WHEN** commune "Strasbourg" was already geocoded in a previous pipeline run
- **THEN** the system SHALL return cached coordinates without calling any API

### Requirement: GeoResult output format
The geocoder SHALL return a `GeoResult` dataclass with fields: `latitude` (float), `longitude` (float), `precision` (enum: exact/approx/centroide), `source_api` (str), `raw_response` (dict for debugging).

#### Scenario: GeoResult from successful geocoding
- **WHEN** BAN returns coordinates for "Haguenau"
- **THEN** the GeoResult SHALL have `precision="exact"`, `source_api="ban"`, and valid lat/lon
