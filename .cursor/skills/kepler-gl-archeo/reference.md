# Kepler.gl — Référence configurations

## Config JSON complète — Sites par TypeSite

Template de configuration réutilisable. Remplacer `"sites"` par le nom exact du dataset passé à `KeplerGl(data={"sites": ...})`.

```python
CONFIG_TYPE_SITE = {
    "version": "v1",
    "config": {
        "visState": {
            "filters": [],
            "layers": [
                {
                    "id": "sites-layer",
                    "type": "point",
                    "config": {
                        "dataId": "sites",
                        "label": "Sites âge du Fer",
                        "columns": {"lat": "latitude", "lng": "longitude"},
                        "isVisible": True,
                        "visConfig": {
                            "radius": 12,
                            "opacity": 0.8,
                            "colorRange": {
                                "name": "TypeSite",
                                "type": "qualitative",
                                "category": "Custom",
                                "colors": [
                                    "#E31A1C",  # oppidum
                                    "#1F78B4",  # habitat
                                    "#6A3D9A",  # nécropole
                                    "#FF7F00",  # dépôt
                                    "#33A02C",  # sanctuaire
                                    "#B15928",  # atelier
                                    "#FB9A99",  # tumulus
                                    "#A6CEE3",  # voie
                                    "#B2DF8A",  # indéterminé
                                ],
                            },
                        },
                        "colorField": {
                            "name": "type_site",
                            "type": "string",
                        },
                    },
                }
            ],
            "interactionConfig": {
                "tooltip": {
                    "enabled": True,
                    "fieldsToShow": {
                        "sites": [
                            {"name": "nom_site", "format": None},
                            {"name": "type_site", "format": None},
                            {"name": "periodes", "format": None},
                            {"name": "commune", "format": None},
                            {"name": "pays", "format": None},
                            {"name": "precision_localisation", "format": None},
                        ]
                    },
                },
                "brush": {"enabled": False},
            },
        },
        "mapState": {
            "latitude": 48.3,
            "longitude": 7.7,
            "zoom": 8,
        },
        "mapStyle": {
            "styleType": "dark",
        },
    },
}
```

## Config — Sites par Période

```python
CONFIG_PERIODE = {
    "version": "v1",
    "config": {
        "visState": {
            "filters": [],
            "layers": [
                {
                    "id": "periodes-layer",
                    "type": "point",
                    "config": {
                        "dataId": "sites",
                        "label": "Périodes",
                        "columns": {"lat": "latitude", "lng": "longitude"},
                        "isVisible": True,
                        "visConfig": {
                            "radius": 12,
                            "opacity": 0.8,
                            "colorRange": {
                                "name": "Periode",
                                "type": "qualitative",
                                "category": "Custom",
                                "colors": [
                                    "#D95F02",  # Hallstatt
                                    "#1B9E77",  # La Tène
                                    "#7570B3",  # Hallstatt/La Tène
                                    "#999999",  # indéterminé
                                ],
                            },
                        },
                        "colorField": {
                            "name": "periodes",
                            "type": "string",
                        },
                    },
                }
            ],
            "interactionConfig": {
                "tooltip": {
                    "enabled": True,
                    "fieldsToShow": {
                        "sites": [
                            {"name": "nom_site", "format": None},
                            {"name": "periodes", "format": None},
                            {"name": "type_site", "format": None},
                            {"name": "commune", "format": None},
                            {"name": "pays", "format": None},
                        ]
                    },
                },
            },
        },
        "mapState": {
            "latitude": 48.3,
            "longitude": 7.7,
            "zoom": 8,
        },
        "mapStyle": {
            "styleType": "dark",
        },
    },
}
```

## Config — Niveau de confiance (opacité)

```python
CONFIG_CONFIANCE = {
    "version": "v1",
    "config": {
        "visState": {
            "layers": [
                {
                    "id": "confiance-layer",
                    "type": "point",
                    "config": {
                        "dataId": "sites",
                        "label": "Confiance localisation",
                        "columns": {"lat": "latitude", "lng": "longitude"},
                        "isVisible": True,
                        "visConfig": {
                            "radius": 10,
                            "opacity": 0.9,
                            "colorRange": {
                                "name": "Confiance",
                                "type": "qualitative",
                                "category": "Custom",
                                "colors": [
                                    "#1A9850",  # exact
                                    "#FEE08B",  # approx
                                    "#D73027",  # centroïde
                                ],
                            },
                        },
                        "colorField": {
                            "name": "precision_localisation",
                            "type": "string",
                        },
                    },
                }
            ],
        },
        "mapState": {
            "latitude": 48.3,
            "longitude": 7.7,
            "zoom": 8,
        },
        "mapStyle": {
            "styleType": "light",
        },
    },
}
```

## Palettes de couleurs — dictionnaires Python

Pour usage dans du code de préparation de données (ajout d'une colonne `color_hex`) :

```python
COLORS_TYPE_SITE = {
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

COLORS_PERIODE = {
    "Hallstatt": "#D95F02",
    "La Tène": "#1B9E77",
    "Hallstatt/La Tène": "#7570B3",
    "indéterminé": "#999999",
}

COLORS_PRECISION = {
    "exact": "#1A9850",
    "approx": "#FEE08B",
    "centroïde": "#D73027",
}

COLORS_PAYS = {
    "FR": "#3366CC",
    "DE": "#DC3912",
    "CH": "#FF9900",
}
```

## Centre de la carte — Rhin supérieur

Coordonnées par défaut pour cadrer la zone d'étude :

| Paramètre | Valeur | Description |
|---|---|---|
| latitude | 48.3 | Centre Alsace |
| longitude | 7.7 | Rhin supérieur |
| zoom | 8 | Tri-national FR/DE/CH |
| zoom (Alsace seule) | 9 | Bas-Rhin + Haut-Rhin |
| zoom (site unique) | 13 | Détail local |

## Fond de carte recommandé

| Contexte | `styleType` |
|---|---|
| Présentation / publication | `"dark"` |
| Travail / analyse | `"light"` |
| Relief / topographie | `"satellite"` |

## Champs GeoJSON disponibles (pipeline BaseFerRhin)

Champs exportés par `GeoJSONExporter` et exploitables dans Kepler :

| Champ | Type | Filtrable | Tooltip |
|---|---|---|---|
| `nom_site` | string | oui | oui |
| `type_site` | string | oui (catégoriel) | oui |
| `periodes` | string | oui (catégoriel) | oui |
| `commune` | string | oui | oui |
| `pays` | string | oui (catégoriel) | oui |
| `region_admin` | string | oui | oui |
| `precision_localisation` | string | oui (catégoriel) | oui |
| `surface_m2` | float | oui (range) | oui |
| `altitude_m` | float | oui (range) | oui |
| `statut_fouille` | string | oui (catégoriel) | oui |
| `description` | string | non | oui |
