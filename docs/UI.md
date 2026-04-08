# Interfaces web

Deux interfaces complémentaires : **Dash** (exploration / filtres / statistiques) et **Kepler.gl** (analyse spatiale avancée).

## 1. Dash — Explorateur interactif

### Stack

- **Dash** >= 2.14 + **dash-bootstrap-components** >= 1.5 (thème DARKLY)
- **Plotly** Scattermapbox (tuiles OpenStreetMap, aucune clé API)
- Police **Inter** (Google Fonts)

### Installation et lancement

```bash
pip install -e ".[ui]"
python -m src.ui
# → http://127.0.0.1:8050
```

### Architecture des modules

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
├── site_loader.py          Chargement données multi-source
└── site_map.py             Construction carte Plotly Scattermapbox
```

### Chargement des données (`site_loader.py`)

Le loader essaie 3 sources par ordre de priorité :

1. `data/output/sites.geojson` — sortie pipeline complète (503 sites)
2. `tests/fixtures/golden_sites.json` — 20 sites de référence (fallback)
3. `data/sources/golden_sites.csv` — données brutes (fallback minimal)

DataFrame Pandas unifié. Les champs complexes (`variantes_nom`, `identifiants_externes`) sont sérialisés en chaînes pour la DataTable Dash.

### Layout

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

### Composants

#### Carte interactive (`site_map.py`)

- Plotly `Scattermapbox` avec tuiles `open-street-map`
- Une trace par catégorie (type de site ou période) pour légende interactive
- Hover : nom, type, période, commune, pays
- Clic : ouvre le panneau de détail (Offcanvas)

#### Frise chronologique (`chronology_chart.py`)

- Barres horizontales pour 6 sous-périodes : Ha C, Ha D, LT A, LT B, LT C, LT D
- Largeur proportionnelle à la durée, couleur Hallstatt/La Tène
- Annotation du nombre de sites par sous-période

#### Filtres (`layout.py`)

| Filtre | Type | Comportement |
|---|---|---|
| Période | Dropdown multi-sélection | Filtre par `str.contains` |
| Type de site | Dropdown multi-sélection | Filtre exact |
| Pays | Checklist (FR, DE, CH) | Tous cochés par défaut |
| Colorer par | Radio (type / période) | Change la coloration carte |

#### Panneau de détail (`callbacks.py`)

Offcanvas latéral (380px) déclenché par clic carte ou sélection tableau. Affiche tous les champs : coordonnées L93, datation, altitude, sources, description, identifiants externes.

#### Tableau des sites (`layout.py`)

DataTable Dash avec tri et filtre natifs. 12 lignes par page. Les champs liste/dict sont sérialisés en chaînes (virgules).

### Palettes de couleurs (`archaeo_palettes.py`)

Alignées avec le skill `kepler-gl-archeo` pour cohérence inter-interfaces.

#### TypeSite

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

#### Période

| Période | Hex |
|---|---|
| Hallstatt | `#D95F02` |
| La Tène | `#1B9E77` |
| Transition | `#7570B3` |
| indéterminé | `#999999` |

### Thème CSS (`assets/archeo.css`)

Thème sombre : background `#0f0f1a`, surface `#16182d`, bordures `#2a2d50`, accent bronze `#C47D3B`, navbar gradient + liseré Hallstatt.

## 2. Kepler.gl — Analyse spatiale avancée

### Stack

- **React 18** + **Vite 6** (frontend)
- **@kepler.gl** 3.1.7 + **@deck.gl** 8.9 (cartographie WebGL)
- **Express 4** + **@duckdb/node-api** 1.5 (serveur API)
- Thème sombre étendu depuis `@kepler.gl/styles`

### Installation et lancement

```bash
cd src/keplergl
npm install
python scripts/build_duckdb.py   # Convertit pipeline JSON → DuckDB
npm start                         # → http://localhost:3001
```

### Architecture

```
src/keplergl/
├── src/
│   ├── App.tsx              KeplerGl + chargement données API
│   ├── kepler-config.ts     Layers, tooltip, interactions, couleurs
│   ├── map-styles.ts        Styles cartes libres (CARTO dark/light, OSM)
│   ├── store.ts             Redux store (kepler middleware)
│   └── main.tsx             Point d'entrée React
├── server/
│   └── index.js             Express API read-only sur DuckDB
├── scripts/
│   └── build_duckdb.py      Conversion VALIDATE.json → DuckDB (L93 → WGS84)
├── data/
│   └── sites.duckdb         Base générée (503 sites + phases + sources)
├── package.json             Dépendances npm
├── vite.config.ts           Config build Vite
└── dist/                    Build production (npm run build)
```

### API endpoints (Express)

| Route | Méthode | Description |
|---|---|---|
| `/api/sites` | GET | Tous les sites (JSON) |
| `/api/sites/geojson` | GET | GeoJSON FeatureCollection (WGS84) |
| `/api/phases` | GET | Toutes les phases |
| `/api/sources` | GET | Toutes les sources bibliographiques |
| `/api/stats` | GET | Statistiques agrégées |
| `/api/site/:siteId` | GET | Détail d'un site + phases + sources |
| `/api/query` | POST | SQL explorer read-only |

### Configuration cartographique (`kepler-config.ts`)

- Layer point coloré par `type_site` (palette alignée sur `archaeo_palettes`)
- Tooltip : nom, type, période, commune, pays, datation
- Interactions : brush, zoom, select, tooltip
- Styles de carte : CARTO dark matter, OSM, satellite

### Script `build_duckdb.py`

Lit `data/processed/VALIDATE.json`, crée 4 tables (`sites`, `phases`, `sources`, `raw_records`) et 2 vues (`sites_with_phases`, `sites_geojson`). Reprojette L93 → WGS84 pour les colonnes `latitude`/`longitude`.

## 3. Kepler.gl Jupyter (skill)

Pour utilisation en notebook :

```bash
pip install -e ".[viz]"
python .cursor/skills/kepler-gl-archeo/scripts/visualize.py data/output/sites.geojson
```

Voir `.cursor/skills/kepler-gl-archeo/SKILL.md` pour les configurations et palettes.
