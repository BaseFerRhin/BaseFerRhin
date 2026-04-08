# BaseFerRhin

Inventaire normalisé des sites de l'**âge du Fer** du **Rhin supérieur** — pipeline ETL Python avec 16 sources hétérogènes, extraction OCR Gallica, géocodage multi-fournisseur et deux interfaces cartographiques interactives. Coordonnées internes en **Lambert-93 (EPSG:2154)**.

### Interface Dash

![Interface Dash — carte, filtres, frise chronologique et statistiques](docs/images/dash-ui.jpg)

### Kepler.gl (Node.js / React / DuckDB)

![Kepler.gl — carte interactive des sites archéologiques](docs/images/kepler-map.jpg)

## Périmètre

### Géographique

| Région | Département/Canton | Pays |
|---|---|---|
| Alsace | Bas-Rhin (67), Haut-Rhin (68) | FR |
| Bade-Wurtemberg | Südbaden, Nordbaden | DE |
| Canton de Bâle | Bâle-Ville, Bâle-Campagne | CH |

### Chronologique

| Période | Datation | Sous-périodes |
|---|---|---|
| Hallstatt | env. -800 à -450 | Ha C, Ha D1, Ha D2, Ha D3 |
| La Tène | env. -450 à -25 | LT A, LT B1, LT B2, LT C1, LT C2, LT D1, LT D2 |

### Types de sites

Oppidum, habitat, nécropole, dépôt, sanctuaire, atelier, voie, tumulus.

## Sources de données (16)

### Tier 1 — Sources primaires

| Source | Type | Extracteur | Records |
|---|---|---|---|
| ArkeoGIS LoupBernard | CSV | `ArkeoGISExtractor` | Bade-Wurtemberg |
| ArkeoGIS ADAB 2011 | CSV | `ArkeoGISExtractor` | Nordbaden (filtre âge du Fer) |
| Patriarche DRAC | XLSX + DBF | `PatriarcheExtractor` | Base nationale + coords `ea_fr.dbf` |
| ea_fr.dbf | DBF | `DBFExtractor` | Coordonnées et chrono Patriarche |
| Alsace-Basel | XLSX multi-feuilles | `AlsaceBaselExtractor` | Base relationnelle (sites, occupations, mobilier) |
| BdD Proto Alsace | XLSX | `BdDProtoAlsaceExtractor` | Inventaire proto, filtrage Bronze/Fer |
| Nécropoles BFIIIb-HaD3 | XLSX | `NecropoleExtractor` | Alsace-Lorraine, coords L93 |
| Inhumations en silos | XLSX | `InhumationsSilosExtractor` | Agrégation individus → sites, 14C |
| Habitats-tombes riches | XLSX | `HabitatsTombesRichesExtractor` | Alsace-Lorraine, pays FR/DE/CH |

### Tier 2 — Enrichissement

| Source | Type | Extracteur | Rôle |
|---|---|---|---|
| AFEAF funéraire | XLSX | `AFEAFExtractor` | Header hiérarchique 2 niveaux |
| AFEAF linéaire | DBF | `DBFExtractor` | Données linéaires |
| Mobilier sépultures | ODS | `ODSExtractor` | Coordonnées Lambert-93 |
| CAG 68 texte | DOC | `_CAGDocExtractor` | Notices par commune et lieu-dit |
| CAG 68 index/biblio | DOC | `DocExtractor` | Index et bibliographie |
| Gallica (BnF) | OCR/SRU | `GallicaExtractor` | CAG 67/68, Cahiers alsaciens |
| Golden set | CSV | `CSVExtractor` | 20 sites de référence validés |

### Résultats du pipeline

| Métrique | Valeur |
|---|---|
| Records bruts ingérés | 2 007 (après filtre chrono/géo) |
| Sites normalisés | 1 589 |
| Sites après déduplication | **503** |
| Sites géolocalisés | 500 / 503 |
| Phases d'occupation | 795 |
| Sources bibliographiques | 1 298 |
| Répartition par pays | FR : 288, DE : 215 |
| Répartition par période | Hallstatt : 246, La Tène : 242, indét. : 307 |
| Types dominants | habitat : 132, nécropole : 131, oppidum : 88 |

## Installation

```bash
pip install -e ".[dev,rawdata]"
```

Groupes optionnels :

```bash
pip install -e ".[ui]"      # Interface web Dash
pip install -e ".[viz]"     # Visualisation Kepler.gl (Jupyter)
pip install -e ".[rawdata]" # Extraction RawData (dbfread, odfpy)
```

Prérequis système :

```bash
# macOS
brew install tesseract antiword

# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-deu antiword
```

- `tesseract` avec packs `fra` et `deu` — OCR Gallica et CAG 67 PDF
- `antiword` — extraction `.doc` OLE2 (CAG 68)

## Utilisation

### Pipeline ETL complet

```bash
python -m src --config config.yaml
```

8 étapes séquentielles avec checkpoints idempotents :

```
DISCOVER → INGEST → EXTRACT → NORMALIZE → DEDUPLICATE → GEOCODE → VALIDATE → EXPORT
```

Reprise depuis une étape :

```bash
python -m src --config config.yaml --start-from NORMALIZE
```

### Interface Dash

```bash
python -m src.ui
# → http://127.0.0.1:8050
```

### Kepler.gl (standalone React + DuckDB)

```bash
cd src/keplergl
python scripts/build_duckdb.py    # Convertit EXPORT.json → DuckDB
npm start                          # → http://localhost:3001
```

## Exports

| Format | Fichier | Description |
|---|---|---|
| GeoJSON | `data/output/sites.geojson` | Points EPSG:4326 (reprojection auto depuis L93) |
| CSV | `data/output/sites.csv` | UTF-8 BOM, colonnes `x_l93`/`y_l93` (EPSG:2154) |
| SQLite | `data/output/sites.sqlite` | Tables `sites`, `phases`, `sources` avec FK |
| DuckDB | `src/keplergl/data/sites.duckdb` | 4 tables + 2 vues (lat/lon WGS84 calculés) |

## Architecture

```
src/
├── domain/              18 fichiers — modèles, normalisation, validation, filtres, déduplication
│   ├── models/          Site, PhaseOccupation, Source, RawRecord, 7 enums
│   ├── normalizers/     Type, période, datation, toponymie (FR/DE), composite
│   ├── validators/      Cohérence chronologique et géographique
│   ├── filters/         Filtre chrono (âge du Fer vs Bronze) et géo (départements, pays)
│   └── deduplication/   Scoring fuzzy (identifiants + nom + coords), union-find, merge
├── infrastructure/      32 fichiers — extracteurs, géocodage, persistance
│   ├── extractors/      16 extracteurs : Gallica, ArkeoGIS, Patriarche, Alsace-Basel, CAG...
│   ├── geocoding/       BAN, Nominatim, GeoAdmin, multi-provider, reprojector, cache
│   └── persistence/     Export CSV, GeoJSON, SQLite, stats Rich
├── application/         5 fichiers — pipeline ETL 8 étapes, config YAML, review queue
├── keplergl/            React/Vite + Express/DuckDB + script build_duckdb.py
└── ui/                  9 fichiers — Dash app, carte Plotly, frise chronologique, filtres
```

**86 fichiers Python** | **13 modules de test** | **Python ≥ 3.11** | **Hatchling**

## Tests

```bash
pytest                    # 140 tests, ~4s
```

| Module | Couverture |
|---|---|
| `test_chrono_filter.py` | Filtre âge du Fer, exclusion Bronze pur, filtre département |
| `test_datation_parser.py` | Parsing dates composites, formats hétérogènes |
| `test_models.py` | Modèles Pydantic, contraintes, validateurs |
| `test_normalizers.py` | Normalisation type/période/toponymie |
| `test_validators.py` | Cohérence chrono/géo |
| `test_deduplication.py` | Scoring, exact ID match, merge, review queue |
| `test_arkeogis_extractor.py` | ArkeoGIS CSV, filtre chrono, pays DE |
| `test_patriarche_extractor.py` | Patriarche XLSX + DBF coords + chrono EUR |
| `test_dbf_extractor.py` | DBF extraction, encoding, column mapping |
| `test_reprojector.py` | Reprojection multi-EPSG, bounds check, NaN/inf |
| `test_thematic_xlsx.py` | Proto, Nécropoles, Inhumations, Habitats riches |
| `test_tier2_extractors.py` | AFEAF, ODS, DOC/antiword, Alsace-Basel |
| `test_export.py` | Export CSV, GeoJSON, SQLite (FK) |

## Documentation

| Document | Contenu |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Clean Architecture, diagrammes de flux, inventaire code, dépendances |
| [Domaine](docs/DOMAIN.md) | Modèles Pydantic, enums, normalisation, validation, déduplication |
| [Pipeline](docs/PIPELINE.md) | 8 étapes ETL, 16 extracteurs, filtrage, géocodage, configuration |
| [Sources de données](docs/DATA-SOURCES.md) | Catalogue des 16 sources, formats, champs, extracteurs |
| [Interface web](docs/UI.md) | Application Dash + Kepler.gl, composants, palettes, thème |

## Licence

MIT
