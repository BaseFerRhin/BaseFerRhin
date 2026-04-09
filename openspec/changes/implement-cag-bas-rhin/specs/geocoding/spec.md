## ADDED Requirements

### Requirement: Commune geocoding via BAN API

The system SHALL geocode each commune found in the PDF by querying the API BAN (Base Adresse Nationale) at `https://api-adresse.data.gouv.fr/search/` with the commune name and department code 67. Requests MUST be throttled to max 10 per second (configurable via `config.yaml` key `geocoding.throttle_rps`).

#### Scenario: Successful geocoding
- **WHEN** geocoding commune "Achenheim" in department 67
- **THEN** the API returns coordinates and the communes table is updated with `latitude`, `longitude` (WGS84) and `x_l93`, `y_l93` (Lambert-93 via pyproj)

#### Scenario: Commune not found by BAN
- **WHEN** the BAN API returns no result for a commune name
- **THEN** the commune's coordinates remain NULL and a WARNING is logged

#### Scenario: API unavailable (offline mode)
- **WHEN** the BAN API is unreachable and a `communes_geo.json` cache file exists
- **THEN** coordinates are loaded from the cache file instead

### Requirement: GeoJSON cache file

The system SHALL write geocoded commune centroids to `data/communes_geo.json` in GeoJSON FeatureCollection format after geocoding, and read from it when available.

#### Scenario: Cache creation
- **WHEN** geocoding completes successfully
- **THEN** a GeoJSON file is written with one Feature per commune containing coordinates and commune_id/commune_name properties

#### Scenario: Cache reuse
- **WHEN** `communes_geo.json` exists and geocoding is re-run
- **THEN** only communes without coordinates are re-geocoded (incremental update)

### Requirement: Coordinate reprojection

The system SHALL convert WGS84 coordinates (lat/lon) to Lambert-93 (EPSG:2154) using pyproj and store both in the communes table.

#### Scenario: WGS84 to Lambert-93
- **WHEN** a commune has WGS84 coordinates lat=48.58, lon=7.60
- **THEN** the corresponding Lambert-93 x_l93 and y_l93 values are computed and stored
