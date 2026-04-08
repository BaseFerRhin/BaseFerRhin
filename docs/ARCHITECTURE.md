# Architecture

## Vue d'ensemble

BaseFerRhin suit une **Clean Architecture** organisée en 4 couches. Chaque couche ne dépend que des couches intérieures. Le domaine est pur (aucune dépendance infra) ; l'infrastructure implémente les ports définis par le domaine.

```
┌────────────────────────────────────────────────────────────┐
│                     Présentation                           │
│         src/ui/ (Dash)  +  src/keplergl/ (React)           │
├────────────────────────────────────────────────────────────┤
│                    src/application/                        │
│          Pipeline ETL 8 étapes, config YAML,               │
│          review queue, orchestration                       │
├────────────────────────────────────────────────────────────┤
│                     src/domain/                            │
│      Modèles Pydantic, normalisation, datation,            │
│      filtres chrono/géo, validation, déduplication          │
├────────────────────────────────────────────────────────────┤
│                  src/infrastructure/                       │
│    16 extracteurs (Gallica, ArkeoGIS, Patriarche, CAG…),   │
│    géocodage multi-pays, reprojection EPSG,                │
│    persistance (GeoJSON, CSV, SQLite, DuckDB)              │
└────────────────────────────────────────────────────────────┘
```

## Inventaire du code source

| Couche | Répertoire | `.py` | Rôle |
|--------|------------|------:|------|
| Présentation | `src/ui/` | 9 | Application Dash, carte Plotly, frise, filtres, callbacks |
| Présentation | `src/keplergl/` | 1 | Script `build_duckdb.py` (+ app React/Vite 7 TS/JS) |
| Application | `src/application/` | 5 | Pipeline, config, pipeline_support, review queue |
| Domaine | `src/domain/models/` | 6 | `Site`, `PhaseOccupation`, `Source`, `RawRecord`, 7 enums |
| Domaine | `src/domain/normalizers/` | 6 | Type, période, datation, toponymie, composite |
| Domaine | `src/domain/validators/` | 3 | Cohérence chrono/géo |
| Domaine | `src/domain/filters/` | 1 | Filtre chronologique (âge du Fer) et géographique |
| Domaine | `src/domain/deduplication/` | 4 | Scoring, deduplicator, merger, scorer |
| Infra | `src/infrastructure/extractors/` | 23 | 16 extracteurs + factory + Gallica (SRU, IIIF, OCR…) |
| Infra | `src/infrastructure/geocoding/` | 8 | BAN, Nominatim, GeoAdmin, multi-provider, reprojector, cache |
| Infra | `src/infrastructure/persistence/` | 5 | CSV, GeoJSON, SQLite, stats |
| Tests | `tests/` | 13 | 140 tests (domain + infrastructure) |
| **Total** | | **86** | |

## Pipeline ETL — flux de données

```
                    config.yaml (16 sources)
                        │
                        ▼
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐
│ DISCOVER │───▶│  INGEST  │───▶│ EXTRACT  │───▶│ NORMALIZE │
│          │    │          │    │          │    │           │
│ SRU      │    │ Factory  │    │ OCR /    │    │ Type      │
│ Gallica  │    │ 16 types │    │ Mentions │    │ Période   │
│          │    │ + filtre │    │          │    │ Toponymie │
│          │    │ chrono   │    │          │    │ Datation  │
└─────────┘    └──────────┘    └──────────┘    └───────────┘
                                                    │
                    ┌───────────────────────────────┘
                    ▼
┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│ DEDUPLICATE │───▶│ GEOCODE  │───▶│ VALIDATE │───▶│ EXPORT │
│             │    │          │    │          │    │        │
│ Exact IDs   │    │ BAN      │    │ Chrono   │    │ CSV    │
│ Scoring     │    │ Nominatim│    │ Géo      │    │ GeoJSON│
│ Union-Find  │    │ GeoAdmin │    │ Review Q │    │ SQLite │
│ Merge       │    │ Cache    │    │          │    │ DuckDB │
└─────────────┘    └──────────┘    └──────────┘    └────────┘
```

## Flux de données quantifié

| Étape | Entrée | Sortie | Volume (run actuel) |
|-------|--------|--------|---------------------|
| DISCOVER | SRU queries | Documents Gallica | ~4 documents |
| INGEST | 16 sources + filtre chrono/géo | `list[RawRecord]` | **2 007 records** |
| EXTRACT | RawRecords | RawRecords enrichis | 2 007 |
| NORMALIZE | RawRecords | `list[Site]` | **1 589 sites** |
| DEDUPLICATE | Sites | Sites uniques + review | **503 sites** |
| GEOCODE | Sites sans coords | Sites géocodés | 500/503 avec coords |
| VALIDATE | Sites | Sites + warnings | 503 |
| EXPORT | Sites | 3 formats | CSV + GeoJSON + SQLite |

## ExtractorFactory — routage des 16 types

```
ExtractorFactory.get_extractor(path, source_type)
    │
    ├── pdf          → PDFExtractor
    ├── csv / xlsx   → CSVExtractor
    ├── arkeogis     → ArkeoGISExtractor          (filter_age_du_fer, pays=DE)
    ├── patriarche   → PatriarcheExtractor         (dbf_path pour coords + chrono)
    ├── dbf          → DBFExtractor                (column_mapping, encoding cp1252)
    ├── alsace_basel  → AlsaceBaselExtractor        (multi-feuilles, reprojection EPSG)
    ├── bdd_proto    → BdDProtoAlsaceExtractor     (colonnes booléennes Fer/Bronze)
    ├── necropoles   → NecropoleExtractor           (filter_departments)
    ├── inhumations  → InhumationsSilosExtractor    (agrégation individus→sites)
    ├── habitats     → HabitatsTombesRichesExtractor (filter_departments, pays)
    ├── afeaf        → AFEAFExtractor               (header hiérarchique 2 niveaux)
    ├── ods          → ODSExtractor                  (odfpy)
    ├── doc          → DocExtractor                  (antiword subprocess)
    ├── cag_doc      → _CAGDocExtractor              (DocExtractor + CAGNoticeExtractor)
    └── fallback     → CSVExtractor (par extension)
```

## Chaîne de filtrage (INGEST)

Après extraction de toutes les sources, le pipeline applique un filtre configurable :

```yaml
filter:
  chrono: true           # Exclure records hors âge du Fer
  departments: [67, 68]  # Bas-Rhin et Haut-Rhin uniquement
```

Le `chrono_filter` implémente :
- Détection Fer par regex (Hallstatt, La Tène, eisenzeit…)
- Exclusion Bronze pur (fin datation <= -800)
- Exclusion par dates numériques hors intervalle [-800, -25]
- Confiance implicite pour certaines méthodes (patriarche, bdd_proto…)
- Logging détaillé par source avec ventilation chrono/geo

## Composant Kepler.gl (standalone)

```
src/keplergl/
├── src/
│   ├── App.tsx              Application React + KeplerGl
│   ├── kepler-config.ts     Config layers, tooltip, couleurs
│   ├── map-styles.ts        Styles cartes libres (CARTO, OSM)
│   ├── store.ts             Redux store pour KeplerGl
│   └── main.tsx             Point d'entrée React
├── server/
│   └── index.js             Express API (DuckDB read-only)
├── scripts/
│   └── build_duckdb.py      Pipeline JSON → DuckDB (L93 → WGS84)
├── data/
│   └── sites.duckdb         Base générée (503 sites + phases + sources)
├── package.json             @kepler.gl 3.1.7, deck.gl 8.9, DuckDB
└── vite.config.ts           Build Vite
```

API endpoints : `/api/sites`, `/api/sites/geojson`, `/api/phases`, `/api/sources`, `/api/stats`, `/api/site/:siteId`, `/api/query` (SQL explorer read-only).

## Dépendances

### Python (pyproject.toml)

| Bibliothèque | Usage |
|---|---|
| `pydantic>=2.0` | Modèles de domaine, validation |
| `httpx>=0.27` | Client HTTP async (Gallica) |
| `tenacity>=8.0` | Retry avec backoff |
| `pdfplumber>=0.11` | Extraction texte/tables PDF |
| `pytesseract>=0.3` | OCR Tesseract (fra+deu) |
| `Pillow>=10.0` | Traitement d'image pré-OCR |
| `rapidfuzz>=3.0` | Scoring fuzzy pour déduplication |
| `pyproj>=3.6` | Reprojection WGS84 ↔ Lambert-93 |
| `geopy>=2.4` | Geocodage (Nominatim, GeoAdmin) |
| `geopandas>=1.0` | Export GeoJSON (reprojection 2154→4326) |
| `sqlite-utils>=3.36` | Export SQLite |
| `lxml>=5.0` | Parsing XML (SRU, ALTO) |
| `openpyxl>=3.1` | Lecture Excel (Patriarche, thématiques) |
| `dbfread>=2.0` | Lecture dBASE (ea_fr.dbf, AFEAF) |
| `odfpy>=1.4` | Lecture ODS (mobilier sépultures) |
| `rich>=13.0` | Affichage console stats |
| `pyyaml>=6.0` | Configuration YAML |

### Node.js (src/keplergl/package.json)

`@kepler.gl/*` 3.1.7, `@deck.gl/*` 8.9.27, `@duckdb/node-api` 1.5.1, React 18, Redux 4, Express 4, Vite 6.

## Arbre des données

```
data/
├── sources/
│   ├── golden_sites.csv              20 sites de référence
│   ├── gallica_metadata.json         Métadonnées SRU Gallica
│   └── gallica_downloads.md          URLs et instructions
├── reference/
│   ├── periodes.json                 Chronologie + patterns FR/DE
│   ├── types_sites.json              Alias TypeSite FR/DE (9 types)
│   ├── toponymes_fr_de.json          Concordance toponymique (~30 entrées)
│   └── gallica_sources.json          4 sources Gallica configurées
├── processed/
│   ├── {STEP}.json                   8 checkpoints pipeline (idempotents)
│   ├── pipeline_log.json             Log append-only avec timestamps
│   ├── geocoder_cache.json           Cache géocodeur JSON
│   └── review_queue.json             Candidats à validation manuelle
├── raw/gallica/                      Cache OCR brut par page IIIF
└── output/
    ├── sites.csv                     Export CSV dénormalisé (EPSG:2154)
    ├── sites.geojson                 Export GeoJSON (EPSG:4326)
    └── sites.sqlite                  Export SQLite normalisé (3 tables)
```
