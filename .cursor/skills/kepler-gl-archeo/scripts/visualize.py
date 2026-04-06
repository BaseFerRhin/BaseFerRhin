"""Visualisation rapide de sites archéologiques avec Kepler.gl.

Usage:
    python .cursor/skills/kepler-gl-archeo/scripts/visualize.py output/sites_age_fer.geojson
    python .cursor/skills/kepler-gl-archeo/scripts/visualize.py data.geojson --color-by periodes --output carte.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
from keplergl import KeplerGl

COLORS_TYPE_SITE = [
    "#E31A1C",  # oppidum
    "#1F78B4",  # habitat
    "#6A3D9A",  # nécropole
    "#FF7F00",  # dépôt
    "#33A02C",  # sanctuaire
    "#B15928",  # atelier
    "#FB9A99",  # tumulus
    "#A6CEE3",  # voie
    "#B2DF8A",  # indéterminé
]

COLORS_PERIODE = [
    "#D95F02",  # Hallstatt
    "#1B9E77",  # La Tène
    "#7570B3",  # Hallstatt/La Tène
    "#999999",  # indéterminé
]

COLORS_PRECISION = [
    "#1A9850",  # exact
    "#FEE08B",  # approx
    "#D73027",  # centroïde
]

COLOR_RANGES = {
    "type_site": {"name": "TypeSite", "colors": COLORS_TYPE_SITE},
    "periodes": {"name": "Période", "colors": COLORS_PERIODE},
    "precision_localisation": {"name": "Précision", "colors": COLORS_PRECISION},
}

MAPSTATE_RHIN_SUPERIEUR = {
    "latitude": 48.3,
    "longitude": 7.7,
    "zoom": 8,
}


def build_config(color_by: str, dataset_name: str) -> dict:
    cr = COLOR_RANGES.get(color_by, COLOR_RANGES["type_site"])
    return {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
                    {
                        "id": "main-layer",
                        "type": "point",
                        "config": {
                            "dataId": dataset_name,
                            "label": f"Sites — {cr['name']}",
                            "columns": {"lat": "latitude", "lng": "longitude"},
                            "isVisible": True,
                            "visConfig": {
                                "radius": 12,
                                "opacity": 0.85,
                                "colorRange": {
                                    "name": cr["name"],
                                    "type": "qualitative",
                                    "category": "Custom",
                                    "colors": cr["colors"],
                                },
                            },
                            "colorField": {"name": color_by, "type": "string"},
                        },
                    }
                ],
                "interactionConfig": {
                    "tooltip": {
                        "enabled": True,
                        "fieldsToShow": {
                            dataset_name: [
                                {"name": "nom_site", "format": None},
                                {"name": "type_site", "format": None},
                                {"name": "periodes", "format": None},
                                {"name": "commune", "format": None},
                                {"name": "pays", "format": None},
                                {"name": "precision_localisation", "format": None},
                            ]
                        },
                    },
                },
            },
            "mapState": MAPSTATE_RHIN_SUPERIEUR,
            "mapStyle": {"styleType": "dark"},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Carte Kepler.gl des sites âge du Fer")
    parser.add_argument("geojson", type=Path, help="Fichier GeoJSON en entrée")
    parser.add_argument(
        "--color-by",
        choices=list(COLOR_RANGES.keys()),
        default="type_site",
        help="Champ de coloration (défaut: type_site)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("carte_sites.html"),
        help="Fichier HTML en sortie (défaut: carte_sites.html)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=700,
        help="Hauteur de la carte en pixels (défaut: 700)",
    )
    parser.add_argument(
        "--save-config",
        type=Path,
        default=None,
        help="Sauvegarder la config JSON après génération",
    )
    args = parser.parse_args()

    if not args.geojson.exists():
        print(f"Fichier introuvable : {args.geojson}", file=sys.stderr)
        sys.exit(1)

    gdf = gpd.read_file(args.geojson)
    print(f"Chargé {len(gdf)} features depuis {args.geojson}")

    dataset_name = "sites"
    config = build_config(args.color_by, dataset_name)
    m = KeplerGl(height=args.height, data={dataset_name: gdf}, config=config)

    m.save_to_html(file_name=str(args.output), read_only=True)
    print(f"Carte exportée → {args.output}")

    if args.save_config:
        args.save_config.parent.mkdir(parents=True, exist_ok=True)
        args.save_config.write_text(json.dumps(m.config, indent=2, ensure_ascii=False))
        print(f"Config sauvegardée → {args.save_config}")


if __name__ == "__main__":
    main()
