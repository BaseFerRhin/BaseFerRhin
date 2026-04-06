# UI BaseFerRhin — Explorateur cartographique

## Vision

Application web interactive pour explorer l'inventaire des sites de l'âge du Fer du Rhin supérieur (Alsace, Bade-Wurtemberg, Bâle). Carte interactive + filtres + frise chronologique + tableau.

## Stack technique

- **Python Dash** + `dash-bootstrap-components` (thème sombre)
- **Plotly Scattermapbox** (tuiles OpenStreetMap, aucune clé API requise)
- **Données** : `tests/fixtures/golden_sites.json` (20 sites normalisés) ou `data/output/sites.geojson` si disponible

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│  BaseFerRhin — Sites de l'âge du Fer du Rhin supérieur       │
├───────────┬──────────────────────────────────────────────────┤
│ FILTRES   │                                                  │
│ Période   │              CARTE INTERACTIVE                   │
│ Type      │           (Plotly Scattermapbox)                  │
│ Pays      │          centre: 48.25°N, 7.7°E                  │
│ Colorer   │                                                  │
│───────────│──────────────────────────────────────────────────│
│ STATS     │           FRISE CHRONOLOGIQUE                    │
│ Total     │    Ha C ██ Ha D █████ LT A ██ LT B ███          │
│ Par type  │    LT C ██████ LT D ████                         │
│ Par pays  │──────────────────────────────────────────────────│
│           │           TABLEAU DES SITES                      │
│           │  Nom | Type | Période | Commune | Pays           │
└───────────┴──────────────────────────────────────────────────┘
```

## Interactions

1. **Filtres** : Période (multi), Type (multi), Pays (checkbox) → mise à jour carte + frise + tableau
2. **Clic carte/tableau** : panneau latéral avec détails du site (offcanvas)
3. **Coloration** : par type de site ou par période (radio)
4. **Tri/filtre** natif dans le tableau

## Palettes couleurs

Issues du skill `kepler-gl-archeo` :
- **TypeSite** : oppidum `#E31A1C`, habitat `#1F78B4`, nécropole `#6A3D9A`, dépôt `#FF7F00`, sanctuaire `#33A02C`, atelier `#B15928`, tumulus `#FB9A99`, voie `#A6CEE3`, indéterminé `#B2DF8A`
- **Période** : Hallstatt `#D95F02`, La Tène `#1B9E77`, transition `#7570B3`, indéterminé `#999999`

## Lancement

```bash
pip install -e ".[ui]"
python -m src.ui
```

## Architecture

```
src/ui/
├── assets/archeo.css      # Thème sombre archéologique
├── app.py                 # App factory Dash
├── site_loader.py         # Chargement données (GeoJSON / JSON / CSV)
├── site_map.py            # Figure Plotly carte
├── chronology_chart.py    # Figure Plotly frise
├── archaeo_palettes.py    # Palettes couleurs domaine
├── layout.py              # Layout Dash Bootstrap
└── callbacks.py           # Interactivité (filtres, sélection)
```
