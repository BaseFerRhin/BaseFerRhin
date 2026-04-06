# Architecture

## Vue d'ensemble

BaseFerRhin suit une **Clean Architecture** organisée en 4 couches. Chaque couche ne dépend que des couches intérieures.

```
┌────────────────────────────────────────────────────────────┐
│                        src/ui/                             │
│              Dash web app (présentation)                   │
├────────────────────────────────────────────────────────────┤
│                    src/application/                        │
│          Pipeline ETL, config, orchestration               │
├────────────────────────────────────────────────────────────┤
│                     src/domain/                            │
│      Modèles Pydantic, normalisation, validation,          │
│              déduplication, scoring                        │
├────────────────────────────────────────────────────────────┤
│                  src/infrastructure/                       │
│    Extracteurs (Gallica, CSV, PDF), géocodage,             │
│           persistance (GeoJSON, CSV, SQLite)               │
└────────────────────────────────────────────────────────────┘
```

## Inventaire du code source

| Couche | Répertoire | Fichiers `.py` | Rôle |
|--------|------------|---------------:|------|
| Présentation | `src/ui/` | 9 | Application Dash, carte, filtres |
| Application | `src/application/` | 5 | Pipeline ETL, config YAML, review queue |
| Domaine | `src/domain/models/` | 6 | Modèles Pydantic (`Site`, `PhaseOccupation`, `Source`, `RawRecord`) |
| Domaine | `src/domain/normalizers/` | 5 | Normalisation (type, période, toponymie) |
| Domaine | `src/domain/validators/` | 3 | Cohérence chrono/géo |
| Domaine | `src/domain/deduplication/` | 4 | Scoring, merge, union-find |
| Infra | `src/infrastructure/` | 1 | Package init |
| Infra | `src/infrastructure/extractors/` | 14 | Gallica (SRU, IIIF, OCR, Tesseract, Metadata), CSV, PDF |
| Infra | `src/infrastructure/geocoding/` | 7 | BAN, Nominatim, GeoAdmin, multi-provider, cache |
| Infra | `src/infrastructure/persistence/` | 5 | Export CSV/GeoJSON/SQLite, stats |
| Utilitaire | `src/keplergl/scripts/` | 1 | Conversion DuckDB pour visualisation Kepler.gl |
| Racine | `src/` | 1 | Point d'entrée CLI (`__main__.py`) |
| **Total** | | **61** | |

## Pipeline ETL — flux de données

```
                    config.yaml
                        │
                        ▼
┌─────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐
│ DISCOVER │───▶│ INGEST  │───▶│ EXTRACT  │───▶│ NORMALIZE │
│          │    │         │    │          │    │           │
│ SRU      │    │ Gallica │    │ OCR /    │    │ Type      │
│ queries  │    │ CSV     │    │ PDF /    │    │ Période   │
│          │    │ PDF     │    │ CSV      │    │ Toponymie │
│          │    │ Metadata│    │          │    │           │
└─────────┘    └─────────┘    └──────────┘    └───────────┘
                                                    │
                    ┌───────────────────────────────┘
                    ▼
┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│ DEDUPLICATE │───▶│ GEOCODE  │───▶│ VALIDATE │───▶│ EXPORT │
│             │    │          │    │          │    │        │
│ Scoring     │    │ BAN      │    │ Chrono   │    │ CSV    │
│ Union-Find  │    │ Nominatim│    │ Géo      │    │ GeoJSON│
│ Merge       │    │ GeoAdmin │    │ Review Q │    │ SQLite │
└─────────────┘    └──────────┘    └──────────┘    └────────┘
```

Chaque étape sauvegarde un checkpoint JSON dans `data/processed/{STEP}.json` avec un hash MD5 pour l'idempotence.

## Flux de données par étape

| Étape | Entrée | Sortie | Données |
|-------|--------|--------|---------|
| DISCOVER | `config.yaml` | documents Gallica | ARK, titres, auteurs via SRU |
| INGEST | documents + fichiers locaux + metadata | `list[RawRecord]` | Records bruts (CSV, Gallica metadata, PDF) |
| EXTRACT | pages/fichiers | `list[RawRecord]` | Texte brut, mentions, coordonnées |
| NORMALIZE | `list[RawRecord]` | `list[Site]` | Sites Pydantic normalisés |
| DEDUPLICATE | `list[Site]` | `list[Site]` + review queue | Sites uniques, candidats à revoir |
| GEOCODE | `list[Site]` | `list[Site]` | Coordonnées ajoutées (BAN/Nominatim) |
| VALIDATE | `list[Site]` | `list[Site]` + warnings | Alertes chrono/géo |
| EXPORT | `list[Site]` | `sites.csv`, `sites.geojson`, `sites.sqlite` | 3 formats |

## Dépendances principales

| Bibliothèque | Usage |
|---|---|
| `pydantic>=2.0` | Modèles de domaine, validation |
| `httpx>=0.27` | Client HTTP async (Gallica) |
| `tenacity>=8.0` | Retry avec backoff |
| `pdfplumber>=0.11` | Extraction texte/tables PDF |
| `pytesseract>=0.3` | OCR Tesseract (fra+deu) |
| `Pillow>=10.0` | Traitement d'image pré-OCR |
| `rapidfuzz>=3.0` | Scoring fuzzy pour déduplication |
| `pyproj>=3.6` | Reprojection WGS84 ↔ Lambert-93 (EPSG:2154) |
| `geopy>=2.4` | Geocodage (Nominatim, GeoAdmin) |
| `geopandas>=1.0` | Export GeoJSON (Shapely, reprojection 2154→4326) |
| `sqlite-utils>=3.36` | Export SQLite |
| `lxml>=5.0` | Parsing XML (SRU, ALTO) |
| `rich>=13.0` | Affichage console |
| `pyyaml>=6.0` | Configuration YAML |
| `openpyxl>=3.1` | Lecture Excel |

### Dépendances optionnelles

| Groupe | Bibliothèques | Usage |
|---|---|---|
| `ui` | `dash>=2.14`, `dash-bootstrap-components>=1.5` | Application web |
| `viz` | `keplergl>=0.3` | Carte Kepler.gl (Jupyter) |
| `dev` | `pytest`, `pytest-asyncio`, `respx`, `ruff` | Tests et linting |

## Arbre des fichiers de données

```
data/
├── sources/
│   ├── golden_sites.csv              # 20 sites de référence (entrée pipeline)
│   ├── gallica_metadata.json          # Métadonnées structurées Gallica (SRU harvest)
│   ├── gallica_downloads.md           # URLs de téléchargement et instructions
│   └── pdf/                           # PDFs téléchargés manuellement (CAG 67, 68...)
├── reference/
│   ├── gallica_sources.json           # 4 sources Gallica (CAG 67, 68, CAAH, Déchelette)
│   ├── periodes.json                  # Chronologie Hallstatt/La Tène + patterns FR/DE
│   ├── types_sites.json               # Alias TypeSite FR/DE (8 types)
│   └── toponymes_fr_de.json           # Concordance toponymique (~30 communes)
├── processed/
│   ├── {STEP}.json                    # Checkpoints pipeline (8 fichiers)
│   ├── pipeline_log.json              # Log append-only
│   ├── geocoder_cache.json            # Cache géocodeur
│   └── review_queue.json              # Candidats déduplication à revoir
├── raw/gallica/                       # Cache OCR brut (Tesseract par page IIIF)
└── output/
    ├── sites.csv                      # Export CSV (colonnes x_l93/y_l93, EPSG:2154)
    ├── sites.geojson                  # Export GeoJSON (reprojection auto → EPSG:4326)
    └── sites.sqlite                   # Export SQLite (x_l93/y_l93, tables sites/phases/sources)
```

## Script utilitaire Kepler.gl / DuckDB

`src/keplergl/scripts/build_duckdb.py` — convertit l'état du pipeline (`EXPORT.json`) en base DuckDB avec 4 tables (`sites`, `phases`, `sources`, `raw_records`) et 2 vues (`sites_with_phases`, `sites_geojson`). Utilise le module `duckdb` (non listé dans `pyproject.toml`, à installer séparément).

```bash
python src/keplergl/scripts/build_duckdb.py
```

## Tests

5 modules de test, 1 fixture JSON (20 sites golden set) :

| Fichier | Couverture |
|---|---|
| `tests/domain/test_models.py` | Enums, contraintes PhaseOccupation, Source, Site |
| `tests/domain/test_normalizers.py` | Normalisation type, période, toponymie |
| `tests/domain/test_validators.py` | Cohérence chronologique et géographique |
| `tests/domain/test_deduplication.py` | Scoring, merge, review queue |
| `tests/infrastructure/test_export.py` | Export CSV, GeoJSON, SQLite (FK) |
| `tests/fixtures/golden_sites.json` | 20 sites normalisés (golden set) |
