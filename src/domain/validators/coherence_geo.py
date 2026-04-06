from dataclasses import dataclass
from typing import Optional

UPPER_RHINE_BBOX = {
    "lat_min": 47.0,
    "lat_max": 49.5,
    "lon_min": 6.5,
    "lon_max": 9.0,
}


@dataclass
class GeoWarning:
    field: str
    message: str


def validate_coordinates(
    latitude: Optional[float],
    longitude: Optional[float],
    region_admin: str = "",
) -> list[GeoWarning]:
    warnings: list[GeoWarning] = []

    if latitude is None or longitude is None:
        return warnings

    bbox = UPPER_RHINE_BBOX
    if latitude < bbox["lat_min"] or latitude > bbox["lat_max"]:
        warnings.append(
            GeoWarning(
                "latitude",
                f"latitude {latitude} hors de la zone attendue ({bbox['lat_min']}–{bbox['lat_max']})",
            )
        )
    if longitude < bbox["lon_min"] or longitude > bbox["lon_max"]:
        warnings.append(
            GeoWarning(
                "longitude",
                f"longitude {longitude} hors de la zone attendue ({bbox['lon_min']}–{bbox['lon_max']})",
            )
        )

    return warnings
