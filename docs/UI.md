# Interface web

Application Dash interactive pour explorer les sites archéologiques sur carte.

## Stack

- **Dash** ≥ 2.14 + **dash-bootstrap-components** ≥ 1.5 (thème DARKLY)
- **Plotly** Scattermapbox (tuiles OpenStreetMap, aucune clé API)
- Police **Inter** (Google Fonts)

## Installation et lancement

```bash
pip install -e ".[ui]"
python -m src.ui
# → http://127.0.0.1:8050
```

## Architecture des modules

```
src/ui/                     9 fichiers Python
├── assets/
│   └── archeo.css          Thème sombre archéologique
├── __init__.py
├── __main__.py             Point d'entrée (python -m src.ui)
├── app.py                  Factory Dash (create_app)
├── archaeo_palettes.py     Palettes couleurs domaine
├── callbacks.py            Callbacks Dash (filtres, carte, détail)
├── chronology_chart.py     Frise chronologique Plotly
├── layout.py               Layout Bootstrap (sidebar + contenu)
└── site_loader.py          Chargement données multi-source
```

## Chargement des données (`site_loader.py`)

Le loader essaie 3 sources par ordre de priorité :

1. `data/output/sites.geojson` — sortie pipeline complète
2. `tests/fixtures/golden_sites.json` — 20 sites de référence (fallback)
3. `data/sources/golden_sites.csv` — données brutes (fallback minimal)

Produit un DataFrame Pandas unifié avec colonnes normalisées : `site_id`, `nom_site`, `type_site`, `periodes`, `sous_periodes`, `commune`, `pays`, `latitude`, `longitude`, etc. Les coordonnées `latitude`/`longitude` (WGS84) sont extraites du GeoJSON (reprojection depuis Lambert-93) ou converties depuis `x_l93`/`y_l93` via `pyproj` pour les sources JSON/CSV.

## Layout

```
┌──────────────────────────────────────────────────────┐
│  BaseFerRhin — Sites de l'âge du Fer du Rhin sup.    │
├──────────┬───────────────────────────────────────────┤
│ FILTRES  │              CARTE                        │
│ Période  │         (Scattermapbox)                   │
│ Type     │     centre: 48.25°N, 7.7°E               │
│ Pays     │          zoom: 7.5                        │
│ Colorer  │                                           │
│──────────├───────────────────────────────────────────┤
│ STATS    │        FRISE CHRONOLOGIQUE                │
│ Total    │    Ha C ██ Ha D █████ LT A ██             │
│ Par type │    LT B ███ LT C █████ LT D ████         │
│ Par pays ├───────────────────────────────────────────┤
│          │        TABLEAU DES SITES                  │
│          │  Site | Type | Période | Commune | Pays   │
└──────────┴───────────────────────────────────────────┘
```

## Composants

### Carte interactive (`site_map.py`)

- **Type** : Plotly `Scattermapbox` avec tuiles `open-street-map`
- **Coloration** : une trace par catégorie (type de site ou période) pour légende interactive
- **Hover** : nom, type, période, commune, pays
- **Clic** : ouvre le panneau de détail (Offcanvas)
- **Taille** : 520px de hauteur

### Frise chronologique (`chronology_chart.py`)

- Barres horizontales pour 6 sous-périodes : Ha C, Ha D, LT A, LT B, LT C, LT D
- Largeur proportionnelle à la durée (en années)
- Couleur : Hallstatt `#D95F02`, La Tène `#1B9E77`
- Annotation du nombre de sites par sous-période

### Filtres (`layout.py`)

| Filtre | Type | Comportement |
|---|---|---|
| Période | Dropdown multi-sélection | Filtre par `str.contains` (gère les multi-périodes) |
| Type de site | Dropdown multi-sélection | Filtre exact |
| Pays | Checklist (FR, DE, CH) | Tous cochés par défaut |
| Colorer par | Radio (type / période) | Change la coloration de la carte |

### Panneau de détail (`callbacks.py`)

Offcanvas latéral (380px) déclenché par clic carte ou sélection tableau. Affiche tous les champs disponibles du site : coordonnées, datation, altitude, surface, sources, description.

### Tableau des sites (`layout.py`)

DataTable Dash avec tri et filtre natifs par colonne. 12 lignes par page, sélection simple pour ouvrir le détail.

## Palettes de couleurs (`archaeo_palettes.py`)

Alignées avec le skill `kepler-gl-archeo` pour cohérence entre l'UI Dash et les exports Kepler.gl/Jupyter.

### TypeSite

| Type | Hex |
|---|---|
| oppidum | `#E31A1C` |
| habitat | `#1F78B4` |
| nécropole | `#6A3D9A` |
| dépôt | `#FF7F00` |
| sanctuaire | `#33A02C` |
| atelier | `#B15928` |
| tumulus | `#FB9A99` |
| voie | `#A6CEE3` |
| indéterminé | `#B2DF8A` |

### Période

| Période | Hex |
|---|---|
| Hallstatt | `#D95F02` |
| La Tène | `#1B9E77` |
| Transition | `#7570B3` |
| indéterminé | `#999999` |

## Thème CSS (`assets/archeo.css`)

Thème sombre personnalisé avec tons archéologiques :
- Background : `#0f0f1a` (bleu nuit)
- Surface : `#16182d`
- Bordures : `#2a2d50`
- Accent : `#C47D3B` (bronze)
- Barre navbar : gradient + liseré Hallstatt orange

## Visualisation avancée (Kepler.gl)

Pour des analyses spatiales avancées, le skill `kepler-gl-archeo` fournit :

```bash
pip install -e ".[viz]"
python .cursor/skills/kepler-gl-archeo/scripts/visualize.py data/output/sites.geojson
```

Voir `.cursor/skills/kepler-gl-archeo/SKILL.md` pour les configurations et palettes détaillées.
