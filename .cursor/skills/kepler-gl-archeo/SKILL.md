---
name: kepler-gl-archeo
description: Visualise des sites archéologiques de l'âge du Fer sur des cartes interactives Kepler.gl via le widget Python/Jupyter. Charge des GeoJSON ou GeoDataFrames, applique des palettes par TypeSite/Période/Confiance, filtre par chronologie et exporte en HTML. Utiliser quand l'utilisateur mentionne Kepler, kepler.gl, carte interactive, visualisation spatiale, visualiser les sites, ou export HTML de carte.
---

# Kepler.gl — Visualisation archéologique

Skill pour créer des cartes interactives de sites protohistoriques (Hallstatt / La Tène) du Rhin supérieur avec **keplergl** en Python/Jupyter.

## Prérequis

```bash
pip install "keplergl>=0.3"
```

Le projet fournit déjà `geopandas` et `shapely` — keplergl est la seule dépendance à ajouter. Déclarée dans `pyproject.toml` sous `[project.optional-dependencies] viz`.

## Quick Start

```python
from keplergl import KeplerGl
import geopandas as gpd

gdf = gpd.read_file("data/output/sites.geojson")
m = KeplerGl(height=600, data={"sites": gdf})
m
```

## Workflow type

### 1. Charger les données

Kepler accepte directement les **GeoDataFrame** (reprojetés en EPSG:4326 automatiquement), les fichiers **GeoJSON**, les **DataFrame** avec colonnes lat/lon, et le **CSV**.

```python
# Depuis le GeoJSON exporté par le pipeline
gdf = gpd.read_file("data/output/sites.geojson")
m = KeplerGl(data={"sites": gdf})

# Ou depuis un DataFrame brut avec lat/lon
m.add_data(data=df, name="sites_raw")
```

### 2. Appliquer une configuration

Capturer la config interactive puis la réutiliser :

```python
# Après personnalisation manuelle dans le widget
config = m.config

# Réappliquer sur de nouvelles données
m2 = KeplerGl(height=600, data={"sites": gdf}, config=config)
```

**Important** : les `dataId` dans la config doivent correspondre aux noms de datasets passés dans `data={}`.

### 3. Exporter

```python
m.save_to_html(file_name="carte_sites.html", read_only=True)
```

`read_only=True` masque le panneau latéral pour un rendu de consultation.

## Configurations archéologiques

### Couleurs par TypeSite

| TypeSite | Couleur | Hex |
|---|---|---|
| oppidum | Rouge vif | `#E31A1C` |
| habitat | Bleu | `#1F78B4` |
| nécropole | Violet | `#6A3D9A` |
| dépôt | Or | `#FF7F00` |
| sanctuaire | Vert | `#33A02C` |
| atelier | Marron | `#B15928` |
| tumulus | Rose | `#FB9A99` |
| voie | Gris | `#A6CEE3` |
| indéterminé | Gris clair | `#B2DF8A` |

### Couleurs par Période

| Période | Couleur | Hex |
|---|---|---|
| Hallstatt | Orange profond | `#D95F02` |
| La Tène | Bleu-vert | `#1B9E77` |
| Hallstatt/La Tène | Violet | `#7570B3` |
| indéterminé | Gris | `#999999` |

### Couleurs par NiveauConfiance

| Niveau | Couleur | Hex |
|---|---|---|
| élevé | Vert | `#1A9850` |
| moyen | Jaune | `#FEE08B` |
| faible | Rouge | `#D73027` |

## Script utilitaire

Un script prêt à l'emploi est disponible :

```bash
python .cursor/skills/kepler-gl-archeo/scripts/visualize.py data/output/sites.geojson
```

Options : `--color-by type_site|periodes|precision_localisation` et `--output carte.html`.

Voir [scripts/visualize.py](scripts/visualize.py) pour le code complet.

## Patterns de visualisation recommandés

### Multi-couches (plusieurs datasets)

```python
m = KeplerGl(height=700)
m.add_data(data=gdf_hallstatt, name="hallstatt")
m.add_data(data=gdf_latene, name="la_tene")
```

### Filtrage temporel

Si le GeoJSON contient `date_debut_bce` et `date_fin_bce` :

```python
# Le filtre range dans la config Kepler permet un slider temporel
# Configurer manuellement dans le widget puis capturer m.config
```

### Taille par surface

Mapper `surface_m2` sur le rayon des points pour une visualisation proportionnelle — configurable dans le panneau "Radius" du layer point.

### Tooltip personnalisé

Configurer via le panneau "Interactions" → "Tooltip" pour afficher : `nom_site`, `type_site`, `periodes`, `commune`, `pays`, `precision_localisation`.

## Bonnes pratiques

1. **Toujours travailler en EPSG:4326** — Kepler ne supporte que WGS84
2. **Nommer les datasets** de manière explicite (`"hallstatt_sites"` pas `"data_1"`)
3. **Sauvegarder la config** après chaque session de personnalisation
4. **Séparer les couches** par période ou type pour un contrôle visuel fin
5. **Limiter les champs** dans le GeoJSON — exclure `phases` et `sources` (objets imbriqués non supportés)
6. **Indiquer la précision** — utiliser `precision_localisation` pour moduler l'opacité ou le style de bordure

## Ressources

- Pour les configs détaillées et templates JSON, voir [reference.md](reference.md)
- [Documentation officielle Kepler.gl Jupyter](https://docs.kepler.gl/docs/keplergl-jupyter)
- [API Reference](https://docs.kepler.gl/docs/api-reference)
