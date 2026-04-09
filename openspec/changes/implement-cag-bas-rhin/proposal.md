## Why

Le projet BaseFerRhin dispose d'un PDF majeur non exploité : la **Carte Archéologique de la Gaule 67/1 — Le Bas-Rhin** (735 pages, 209 Mo), qui recense ~998 communes et ~3 000–5 000 sous-notices archéologiques dont 300–600 concernent l'âge du Fer. Ce document est le référentiel le plus complet pour l'archéologie protohistorique du Bas-Rhin, mais son contenu reste inaccessible programmatiquement. L'extraction structurée et la visualisation interactive de ces données permettront d'enrichir considérablement le pipeline BaseFerRhin et de fournir un outil autonome de consultation aux chercheurs.

## What Changes

- **Extraction PDF complète** : pipeline 4 phases (PDF → texte paginé → notices communales → sous-notices → SiteRecord) sur les pages 154–660, avec gestion du layout 2 colonnes via `pdfplumber`
- **Persistance DuckDB** : schéma relationnel 6 tables (communes, notices, periodes, vestiges, bibliographie, figures) + 4 vues analytiques
- **Géocodage communes** : centroïdes WGS84/Lambert-93 via API BAN pour les 998 communes du Bas-Rhin
- **Interface Dash multi-pages** : 4 pages interactives (carte Scattermapbox, navigateur de notices, frise chronologique, dashboard statistiques) avec thème sombre archéologique
- **Export pipeline parent** : conversion DuckDB → JSON `RawRecord` compatible avec l'ETL BaseFerRhin
- **CLI Click** : commandes `extract`, `geocode`, `export`, `stats` et lancement UI
- **Tests unitaires** : 6 modules couvrant chaque phase d'extraction et le stockage

## Capabilities

### New Capabilities

- `pdf-extraction`: Extraction texte du PDF CAG 67/1 page par page avec gestion 2 colonnes, découpage en notices communales et sous-notices
- `iron-age-filtering`: Filtrage des sous-notices par mots-clés de l'âge du Fer (FR+DE), classification des vestiges (9 types distincts incl. tumulus, sanctuaire), estimation de confiance, normalisation des sous-périodes, et construction de SiteRecord typés
- `duckdb-storage`: Schéma DuckDB relationnel pour stocker communes, notices, périodes, vestiges, bibliographie et figures avec vues analytiques
- `geocoding`: Géocodage des communes du Bas-Rhin via API BAN (centroïdes WGS84 et Lambert-93)
- `dash-ui`: Interface web Dash multi-pages : carte interactive, navigateur de notices, chronologie, statistiques
- `pipeline-export`: Export des notices âge du Fer vers le format RawRecord du pipeline parent BaseFerRhin

### Modified Capabilities

## Impact

- **Code** : sous-projet autonome `sub_projet/CAG Bas-Rhin/` — ~20 modules Python, ~12 modules UI
- **Dépendances** : `pdfplumber`, `duckdb`, `dash`, `dash-bootstrap-components`, `pyproj`, `httpx`, `click`, `rich`
- **Données** : génération d'un fichier `cag67.duckdb` (~5–20 Mo) et `communes_geo.json`
- **Pipeline parent** : nouvelle source `cag_duckdb` dans `config.yaml` BaseFerRhin
- **Réseau** : appel API BAN pour géocodage (998 requêtes, throttled)
- **GitHub** : repo dédié `BaseFerRhin/CAG-Bas-Rhin` déjà créé
