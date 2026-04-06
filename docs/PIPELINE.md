# Pipeline ETL

## Vue d'ensemble

Le pipeline traite les sources hétérogènes (Gallica BnF, CSV, PDF) pour produire un inventaire normalisé des sites de l'âge du Fer en 8 étapes séquentielles avec checkpoints.

```
python -m src --config config.yaml [--start-from STEP]
```

## Configuration (`config.yaml`)

```yaml
sources:
  - path: data/sources/golden_sites.csv
    type: csv

gallica_queries:
  - 'dc.title all "carte archéologique Gaule" and dc.title all "Bas-Rhin"'
  - 'dc.title all "carte archéologique Gaule" and dc.title all "68"'
  - 'dc.title all "archéologique" and dc.title all "Alsace"'
  - 'dc.title all "archéologique" and dc.title all "Rhin"'

ocr_quality_threshold: 0.4
dedup_merge_threshold: 0.85
dedup_review_threshold: 0.70
geocoder_cache_path: data/processed/geocoder_cache.json
output_dir: data/output
data_dir: data
log_level: INFO
```

Modèle Pydantic : `PipelineConfig` (`src/application/config.py`), 10 champs dont `gallica_metadata_path` (défaut `data/sources/gallica_metadata.json`).

## Étapes du pipeline

### 1. DISCOVER

Interroge l'API **SRU de Gallica** (BnF) via `GallicaSRUClient`. Pagination par lots de 50 résultats. Parse le XML pour extraire les documents avec leurs identifiants ARK, titres, auteurs et dates.

**Requêtes configurées :** 4 queries SRU ciblant les Cartes Archéologiques de la Gaule et les publications alsaciennes.

### 2. INGEST

Collecte les données de toutes les sources configurées :
- **Métadonnées Gallica** (`GallicaMetadataExtractor`) — parse `gallica_metadata.json` pour extraire communes et types depuis les champs `geographic_scope`, `communes_mentioned` et `mentions_found`
- Documents Gallica découverts (ARK → pages)
- Fichiers locaux déclarés dans `sources[]` (CSV, PDF)

### 3. EXTRACT

Extrait les `RawRecord` depuis chaque source selon son type :

| Extracteur | Format | Méthode |
|---|---|---|
| `CSVExtractor` | `.csv`, `.xlsx` | Détection encodage (utf-8, latin-1, cp1252), sniff séparateur, mapping colonnes → `RawRecord` |
| `PDFExtractor` | `.pdf` | `pdfplumber` page par page : texte + tables dans `extra`, flag `needs_ocr` |
| `GallicaExtractor` | pages Gallica | Pipeline async (voir ci-dessous) |

**Pipeline Gallica** (async) :
1. SRU → documents avec ARK leaf `bpt6k*` uniquement
2. Par page (délai 2s entre requêtes) :
   - Tentative OCR **Tesseract** via IIIF (image JPEG `full/max`) → `pytesseract fra+deu --psm 1 --oem 1`
   - Fallback : texte brut via `texteBrut` URL (avec détection CAPTCHA/HTML)
   - Cache disque : `data/raw/gallica/{ark_path}/f{page}.tesseract.txt`
3. **Scoring qualité OCR** : ratio tokens reconnus dans un lexique français courant
4. Filtrage par `ocr_quality_threshold` (défaut 0.4)
5. **Extraction de mentions** (`GallicaSiteMentionExtractor`) : 3 patterns regex
   - Forward : commune → type de site
   - Reverse : type de site → commune
   - Preposition : "fouilles/découvertes… à COMMUNE"
   - Dédoublonnage par `(commune, type)`

**Composants Gallica et extraction** (14 fichiers) :

| Classe | Fichier | Rôle |
|---|---|---|
| `GallicaSRUClient` | `gallica_sru.py` | Recherche SRU paginée (`https://gallica.bnf.fr/SRU`) |
| `GallicaCache` | `gallica_cache.py` | Cache disque + sémaphore HTTP (2 connexions) |
| `GallicaIIIFClient` | `gallica_iiif.py` | Téléchargement image IIIF `full/max` (retry tenacity) |
| `GallicaOCRClient` | `gallica_ocr.py` | Texte brut Gallica via `texteBrut` (détection CAPTCHA) |
| `OCRQualityScorer` | `gallica_ocr.py` | Score qualité basé sur lexique français |
| `TesseractOCRClient` | `tesseract_ocr.py` | OCR local Tesseract `fra+deu` via Pillow + pytesseract |
| `GallicaSiteMentionExtractor` | `gallica_mention_extractor.py` | Regex extraction communes/types (3 patterns) |
| `GallicaMetadataExtractor` | `gallica_metadata_extractor.py` | Extraction depuis métadonnées structurées JSON |
| `GallicaALTOClient` | `gallica_alto.py` | Parsing XML ALTO (coordonnées blocs texte) |
| `GallicaExtractor` | `gallica_extractor.py` | Orchestrateur async du pipeline OCR complet |
| `ExtractorFactory` | `factory.py` | Routage `.csv`/`.xlsx` → CSV, `.pdf` → PDF |
| `CSVExtractor` | `csv_extractor.py` | Détection encodage, sniff séparateur, mapping colonnes |
| `PDFExtractor` | `pdf_extractor.py` | `pdfplumber` page par page : texte + tables |
| `BaseExtractor` | `base.py` | Classe abstraite (interface) |

### 4. NORMALIZE

Transforme chaque `RawRecord` en `Site` Pydantic normalisé via `SiteNormalizer` :

1. **TypeSiteNormalizer** — alias FR/DE → enum `TypeSite` (8 types + indéterminé)
2. **PeriodeNormalizer** — patterns FR/DE + regex sous-période → `Periode` + `sous_periode`
3. **ToponymeNormalizer** — concordance FR/DE (~30 entrées) → commune canonique
4. Construction du `Site` avec `PhaseOccupation` et `Source`

**Génération des identifiants :**
- `site_id` = `SITE-{MD5(source_path|page|raw_text[:500])}`
- `phase_id` = `{site_id}-p1`
- `source_id` = `{site_id}-src1`

**Mapping `extraction_method` → `TypeSource` :**

| extraction_method | TypeSource |
|---|---|
| `gallica_ocr` | `GALLICA_CAG` |
| `pdf` | `PUBLICATION` |
| autre (csv, tesseract_iiif, gallica_metadata) | `TABLEUR` |

### 5. DEDUPLICATE

Détection et fusion des doublons (voir [DOMAIN.md](DOMAIN.md#déduplication-srcdomaindeduplication) pour l'algorithme détaillé).

- Scoring pairwise (rapidfuzz + distance euclidienne Lambert-93)
- Union-Find avec `merge_threshold=0.85`
- Review queue pour les paires entre 0.70 et 0.85
- Merge par richesse de données

**Sortie :** `review_queue.json` avec les candidats nécessitant une validation manuelle.

### 6. GEOCODE

Géocode les sites sans coordonnées. L'étape GEOCODE dans `pipeline_support.py` utilise directement `BANGeocoder` avec un cache JSON. Le module `MultiGeocoder` est disponible pour un dispatch par pays :

| Pays | Chaîne de géocodeurs |
|---|---|
| FR | BAN (`api-adresse.data.gouv.fr`) → Nominatim (`fr`) |
| DE | Nominatim (`de`) |
| CH | GeoAdmin (`api3.geo.admin.ch`) → Nominatim (`ch`) |

**Reprojection :** les APIs retournent des coordonnées WGS84 (lat/lon). Chaque géocodeur reprojette automatiquement vers Lambert-93 (EPSG:2154) via `wgs84_to_l93()` dans `GeoResult`.

**Cache :** `data/processed/geocoder_cache.json` (clé = commune normalisée, valeurs `x_l93`/`y_l93`).

**Précision :**
- BAN retourne des centroïdes municipaux → `precision = "centroide"`
- Nominatim détermine la précision selon `addresstype`/`type` dans la réponse

### 7. VALIDATE

Applique les validateurs de cohérence sur chaque site :

1. **Cohérence chronologique** — datation dans les bornes de la période, sous-période cohérente
2. **Cohérence géographique** — coordonnées Lambert-93 dans la bounding box du Rhin supérieur (x: 930 000–1 060 000, y: 6 710 000–6 990 000)

Les warnings sont ajoutés à la `review_queue.json`.

### 8. EXPORT

Produit 3 formats de sortie dans `data/output/` :

| Format | Fichier | Détails |
|---|---|---|
| CSV | `sites.csv` | UTF-8 BOM, une ligne par site-phase, colonnes `x_l93`/`y_l93` (EPSG:2154) |
| GeoJSON | `sites.geojson` | EPSG:4326 (reprojection auto depuis Lambert-93), propriétés sans `phases`/`sources` |
| SQLite | `sites.sqlite` | Tables `sites` (`x_l93`/`y_l93`), `phases`, `sources` avec FK |

Affiche les statistiques via `ExportStats` (Rich console) : totaux, ventilation par pays/type/période, taux de géolocalisation.

## Checkpoints et reprise

Chaque étape sauvegarde son état dans `data/processed/{STEP}.json` avec un `input_md5` pour l'idempotence. Le pipeline peut être relancé depuis n'importe quelle étape :

```bash
python -m src --config config.yaml --start-from NORMALIZE
```

Le `pipeline_log.json` enregistre chaque début/fin d'étape avec timestamps et compteurs.

## Stratégie OCR Gallica

Le pipeline utilise deux stratégies complémentaires pour extraire du texte des documents Gallica :

```
Document (ARK bpt6k*)
    │
    ├── Stratégie primaire : IIIF + Tesseract (local)
    │   1. GallicaIIIFClient télécharge l'image JPEG (full/max)
    │   2. TesseractOCRClient redimensionne si > 4000×6000px
    │   3. pytesseract.image_to_string(lang="fra+deu", --psm 1 --oem 1)
    │   4. Cache disque : data/raw/gallica/{ark_path}/f{page}.tesseract.txt
    │
    └── Stratégie fallback : texteBrut Gallica (si Tesseract désactivé)
        1. GallicaOCRClient GET texteBrut URL
        2. Détection CAPTCHA (réponse HTML au lieu de texte)
        3. Retry après 10s, abandon après 3 échecs consécutifs
```

Le sémaphore dans `GallicaCache` limite à 2 connexions HTTP simultanées. Un délai de 2 secondes entre chaque page (`_PAGE_DELAY`) respecte le rate-limiting de Gallica.

## Données de référence

| Fichier | Contenu | Entrées |
|---|---|---|
| `gallica_sources.json` | 4 sources Gallica | CAG 67, CAG 68, CAAH, Déchelette |
| `periodes.json` | Chronologie + patterns | Hallstatt, La Tène, Transition + regex |
| `types_sites.json` | Alias FR/DE | 8 types × ~6 alias chacun |
| `toponymes_fr_de.json` | Concordance toponymique | ~30 communes FR/DE |
