## ADDED Requirements

### Requirement: Multi-EPSG reprojection to Lambert-93
The system SHALL provide a `Reprojector` class that transforms coordinates from any source EPSG to Lambert-93 (EPSG:2154) using `pyproj`.

#### Scenario: Reproject WGS84 to Lambert-93
- **WHEN** input is `(lon=7.58, lat=47.92, epsg=4326)`
- **THEN** output SHALL be `(x_l93, y_l93)` in EPSG:2154 within valid bounds (`100_000 <= x <= 1_200_000`, `6_000_000 <= y <= 7_200_000`)

#### Scenario: Pass-through Lambert-93
- **WHEN** input is `(x=1024887, y=6797044, epsg=2154)`
- **THEN** output SHALL be `(1024887, 6797044)` unchanged

#### Scenario: Reproject Web Mercator
- **WHEN** input is `(x, y, epsg=3857)`
- **THEN** output SHALL be correctly transformed to EPSG:2154

#### Scenario: Unknown EPSG
- **WHEN** input has `epsg=None` or an unrecognized code
- **THEN** the reprojector SHALL raise a `ValueError` with a descriptive message

### Requirement: Transformer caching
The system SHALL cache `pyproj.Transformer` instances by source EPSG to avoid repeated initialization.

#### Scenario: Reuse cached transformer
- **WHEN** 500 points with `epsg=4326` are reprojected sequentially
- **THEN** only 1 `Transformer` instance SHALL be created

### Requirement: Post-reprojection validation
The system SHALL validate that reprojected coordinates fall within Lambert-93 bounds for metropolitan France.

#### Scenario: Valid coordinates
- **WHEN** reprojected `x_l93 = 1024887` and `y_l93 = 6797044`
- **THEN** validation SHALL pass

#### Scenario: Coordinates outside France bounds
- **WHEN** reprojected coordinates fall outside `[100_000, 1_200_000] x [6_000_000, 7_200_000]`
- **THEN** the reprojector SHALL log a warning and return the coordinates with a flag `extra["out_of_bounds"] = true`
