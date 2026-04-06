"""Color palettes for archaeological data visualization (kepler-gl-archeo aligned)."""

TYPE_SITE_COLORS: dict[str, str] = {
    "oppidum": "#E31A1C",
    "habitat": "#1F78B4",
    "nécropole": "#6A3D9A",
    "dépôt": "#FF7F00",
    "sanctuaire": "#33A02C",
    "atelier": "#B15928",
    "tumulus": "#FB9A99",
    "voie": "#A6CEE3",
    "indéterminé": "#B2DF8A",
}

PERIODE_COLORS: dict[str, str] = {
    "Hallstatt": "#D95F02",
    "La Tène": "#1B9E77",
    "Hallstatt/La Tène": "#7570B3",
    "indéterminé": "#999999",
}

PAYS_COLORS: dict[str, str] = {
    "FR": "#3366CC",
    "DE": "#DC3912",
    "CH": "#FF9900",
}

PRECISION_COLORS: dict[str, str] = {
    "exact": "#1A9850",
    "approx": "#FEE08B",
    "centroïde": "#D73027",
}

MAP_CENTER = {"lat": 48.25, "lon": 7.7}
MAP_ZOOM = 7.5

SUB_PERIODS: list[tuple[str, int, int, str]] = [
    ("Ha C", -800, -620, "Hallstatt"),
    ("Ha D", -620, -450, "Hallstatt"),
    ("LT A", -450, -380, "La Tène"),
    ("LT B", -380, -260, "La Tène"),
    ("LT C", -260, -150, "La Tène"),
    ("LT D", -150, -25, "La Tène"),
]
