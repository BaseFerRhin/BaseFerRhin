from dataclasses import dataclass
from typing import Optional

# Upper Rhine bounding box in Lambert-93 (EPSG:2154)
UPPER_RHINE_BBOX = {
    "x_min": 930_000.0,
    "x_max": 1_060_000.0,
    "y_min": 6_710_000.0,
    "y_max": 6_990_000.0,
}


@dataclass
class GeoWarning:
    field: str
    message: str


def validate_coordinates(
    x_l93: Optional[float],
    y_l93: Optional[float],
    region_admin: str = "",
) -> list[GeoWarning]:
    warnings: list[GeoWarning] = []

    if x_l93 is None or y_l93 is None:
        return warnings

    bbox = UPPER_RHINE_BBOX
    if x_l93 < bbox["x_min"] or x_l93 > bbox["x_max"]:
        warnings.append(
            GeoWarning(
                "x_l93",
                f"x_l93 {x_l93:.0f} hors de la zone attendue ({bbox['x_min']:.0f}–{bbox['x_max']:.0f})",
            )
        )
    if y_l93 < bbox["y_min"] or y_l93 > bbox["y_max"]:
        warnings.append(
            GeoWarning(
                "y_l93",
                f"y_l93 {y_l93:.0f} hors de la zone attendue ({bbox['y_min']:.0f}–{bbox['y_max']:.0f})",
            )
        )

    return warnings
