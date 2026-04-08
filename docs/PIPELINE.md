# Pipeline ETL

## Vue d'ensemble

Le pipeline ingère 16 sources hétérogènes (CSV, XLSX, DBF, ODS, DOC, OCR Gallica) pour produire un inventaire normalisé de 503 sites de l'âge du Fer en 8 étapes séquentielles avec checkpoints idempotents.

```bash
python -m src --config config.yaml [--start-from STEP]
```

## Configuration (`config.yaml`)

```yaml
sources:
  - path: "RawData/.../LoupBernard_ArkeoGis.csv"
    type: arkeogis
  - path: "RawData/.../Patriarche_ageFer.xlsx"
    type: patriarche
    options:
      dbf_path: "RawData/.../ea_fr.dbf"
  # ... 16 sources au total (voir DATA-SOURCES.md)

filter:
  chrono: true             # Exclure records hors âge du Fer
  departments: [67, 68]    # Bas-Rhin et Haut-Rhin

gallica_queries:
  - 'dc.title all "carte archéologique Gaule" and dc.title all "Bas-Rhin"'
  - 'dc.title all "carte archéologique Gaule" and dc.title all "68"'
  - 'dc.title all "archéologique" and dc.title all "Alsace"'
  - 'dc.title all "archéologique" and dc.title all "Rhin"'

ocr_quality_threshold: 0.4
dedup_merge_threshold: 0.85
dedup_review_threshold: 0.70
output_dir: data/output
log_level: INFO
```

Modèle Pydantic : `PipelineConfig` + `FilterConfig` (`src/application/config.py`).

## Étapes du pipeline

### 1. DISCOVER

Interroge l'API **SRU de Gallica** (BnF) via `GallicaSRUClient`. Pagination par lots de 50. Parse XML pour extraire les identifiants ARK, titres, auteurs. 4 queries configurées ciblant les Cartes Archéologiques de la Gaule et les publications alsaciennes.

### 2. INGEST

Collecte les données de toutes les sources via `ExtractorFactory` :

| Extracteur | Format | Sources |
|---|---|---|
| `ArkeoGISExtractor` | CSV | LoupBernard, ADAB 2011 |
| `PatriarcheExtractor` | XLSX + DBF | Patriarche DRAC + ea_fr.dbf |
| `DBFExtractor` | DBF | ea_fr.dbf, AFEAF linéaire |
| `AlsaceBaselExtractor` | XLSX multi-feuilles | Alsace-Basel (4 feuilles FK) |
| `BdDProtoAlsaceExtractor` | XLSX | BdD Proto Alsace |
| `NecropoleExtractor` | XLSX | Nécropoles BFIIIb-HaD3 |
| `InhumationsSilosExtractor` | XLSX | Inhumations en silos |
| `HabitatsTombesRichesExtractor` | XLSX | Habitats-tombes riches |
| `AFEAFExtractor` | XLSX | AFEAF funéraire |
| `ODSExtractor` | ODS | Mobilier sépultures |
| `_CAGDocExtractor` | DOC | CAG 68 texte (notices) |
| `DocExtractor` | DOC | CAG 68 index, biblio |
| `GallicaExtractor` | OCR/SRU | Documents Gallica |
| `GallicaMetadataExtractor` | JSON | Métadonnées Gallica structurées |
| `CSVExtractor` | CSV | Golden set (20 sites ref) |

**Filtre chrono/géo** appliqué en fin d'INGEST :

```python
filter_records(rows, chrono=True, departments={67, 68})
```

- Exclut les records Bronze pur (fin <= -800)
- Exclut les textes « âge du Bronze » sans mention Fer
- Exclut les départements hors périmètre
- Fait confiance aux sources spécialisées (patriarche, bdd_proto, afeaf…)
- Logging détaillé par source avec ventilation chrono/geo

**Résultat :** ~2 007 records après filtre.

### 3. EXTRACT

Enrichit les `RawRecord` — extraction de mentions Gallica (patterns regex communes/types), flag `needs_ocr` pour les PDFs.

### 4. NORMALIZE

Transforme chaque `RawRecord` en `Site` Pydantic via `SiteNormalizer` (composite) :

1. `TypeSiteNormalizer` — alias FR/DE → enum `TypeSite` (9 types)
2. `PeriodeNormalizer` — patterns FR/DE + regex sous-période
3. `DatationParser` — dates composites et hétérogènes
4. `ToponymeNormalizer` — concordance FR/DE (~30 communes)
5. Reprojection coordonnées : L93 natif depuis `extra` ou WGS84 → L93
6. Propagation identifiants externes (Patriarche EA, ArkeoGIS ID, Alsace-Basel ID)
7. Détermination pays depuis `extra["pays"]`

**Résultat :** ~1 589 sites.

### 5. DEDUPLICATE

Détection et fusion des doublons (voir [DOMAIN.md](DOMAIN.md#déduplication) pour l'algorithme) :

- **Exact ID match** : Patriarche EA ou ArkeoGIS ID identique → score 1.0
- Scoring pairwise (rapidfuzz + distance Lambert-93)
- Union-Find avec `merge_threshold=0.85`
- Review queue pour paires entre 0.70 et 0.85
- Merge par richesse de données

**Résultat :** **503 sites** uniques (288 FR, 215 DE).

### 6. GEOCODE

Géocode les sites sans coordonnées via chaîne multi-pays :

| Pays | Géocodeurs |
|---|---|
| FR | BAN (`api-adresse.data.gouv.fr`) → Nominatim |
| DE | Nominatim (`de`) |
| CH | GeoAdmin (`api3.geo.admin.ch`) → Nominatim |

Reprojection automatique WGS84 → Lambert-93. Cache JSON persistant.

**Résultat :** 500/503 sites géolocalisés.

### 7. VALIDATE

Validateurs de cohérence :
- **Chronologique** — datation dans les bornes de la période
- **Géographique** — Lambert-93 dans la bounding box Rhin supérieur (x: 930k–1060k, y: 6710k–6990k)

Warnings → `review_queue.json`.

### 8. EXPORT

3 formats dans `data/output/` :

| Format | Fichier | Détails |
|---|---|---|
| CSV | `sites.csv` | UTF-8 BOM, une ligne par site-phase (802 lignes), coords EPSG:2154 |
| GeoJSON | `sites.geojson` | EPSG:4326 (reprojection auto L93→WGS84), 500 features |
| SQLite | `sites.sqlite` | Tables `sites`, `phases`, `sources` avec FK |

Stats Rich console : 503 sites, 795 phases, 1298 sources, ventilation par pays/type/période.

**DuckDB** (pour Kepler.gl) : généré séparément via `build_duckdb.py`, inclut colonnes `latitude`/`longitude` WGS84.

## Checkpoints et reprise

Chaque étape sauvegarde dans `data/processed/{STEP}.json` avec `input_md5` pour l'idempotence. Le pipeline skip une étape si le hash d'entrée correspond au checkpoint existant.

```bash
python -m src --config config.yaml --start-from NORMALIZE
```

Le `pipeline_log.json` enregistre chaque début/fin avec timestamps, compteurs et hash MD5.

Pour forcer une re-exécution complète : supprimer les fichiers `data/processed/*.json`.

## Stratégie OCR Gallica

```
Document (ARK bpt6k*)
    │
    ├── Stratégie primaire : IIIF + Tesseract (local)
    │   1. GallicaIIIFClient télécharge l'image JPEG (full/max)
    │   2. TesseractOCRClient redimensionne si > 4000×6000px
    │   3. pytesseract.image_to_string(lang="fra+deu", --psm 1 --oem 1)
    │   4. Cache disque : data/raw/gallica/{ark_path}/f{page}.tesseract.txt
    │
    └── Stratégie fallback : texteBrut Gallica
        1. GallicaOCRClient GET texteBrut URL
        2. Détection CAPTCHA (HTML au lieu de texte)
        3. Retry après 10s, abandon après 3 échecs
```

Sémaphore 2 connexions HTTP simultanées. Délai 2s entre pages.

## Composants Gallica (14 fichiers)

| Classe | Fichier | Rôle |
|---|---|---|
| `GallicaExtractor` | `gallica_extractor.py` | Orchestrateur async du pipeline OCR |
| `GallicaSRUClient` | `gallica_sru.py` | Recherche SRU paginée |
| `GallicaCache` | `gallica_cache.py` | Cache disque + sémaphore HTTP |
| `GallicaIIIFClient` | `gallica_iiif.py` | Download image IIIF full/max |
| `GallicaOCRClient` | `gallica_ocr.py` | Texte brut Gallica (fallback) |
| `OCRQualityScorer` | `gallica_ocr.py` | Score qualité sur lexique français |
| `TesseractOCRClient` | `tesseract_ocr.py` | OCR local fra+deu |
| `GallicaSiteMentionExtractor` | `gallica_mention_extractor.py` | 3 patterns regex (commune→type, type→commune, préposition) |
| `GallicaMetadataExtractor` | `gallica_metadata_extractor.py` | Extraction depuis métadonnées JSON |
| `GallicaALTOClient` | `gallica_alto.py` | Parsing XML ALTO |

## Données de référence

| Fichier | Contenu |
|---|---|
| `data/reference/periodes.json` | Chronologie Hallstatt/La Tène + patterns regex FR/DE |
| `data/reference/types_sites.json` | 9 types × aliases FR/DE |
| `data/reference/toponymes_fr_de.json` | Concordance toponymique (~30 communes) |
| `data/reference/gallica_sources.json` | 4 sources Gallica configurées |
