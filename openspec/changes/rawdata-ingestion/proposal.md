## Why

Le pipeline ETL de BaseFerRhin ne traite actuellement que 20 sites (golden set CSV) et les sources Gallica (OCR/SRU). Le dossier `RawData/GrosFichiers - Béhague/` contient **16 fichiers bruts** issus de bases archéologiques professionnelles (ArkeoGIS, Patriarche, CAG, AFEAF, bases régionales) représentant ~5 400 enregistrements et ~3 750 sites pertinents âge du Fer. Sans ces données, la base reste un prototype incomplet couvrant <1% du corpus disponible.

## What Changes

- Ajout de **8 nouveaux extracteurs** pour les formats ArkeoGIS CSV, Patriarche XLSX, Alsace-Basel multi-feuilles, AFEAF hiérarchique, DBF, ODS, DOC OLE2, et CAG PDF
- Ajout d'un **parser de datation unifié** capable de traiter 6 formats de datation bruts et d'éclater les fourchettes composites (`Ha C-D`, `LT A-B`) en phases individuelles conformes à `_VALID_SUB_PERIODS`
- Ajout d'un **reprojector multi-EPSG** (WGS84, Lambert-93, variable) vers Lambert-93 via `pyproj`
- Enrichissement du `TypeNormalizer` avec les valeurs allemandes et les types manquants
- Enrichissement du scoring de **déduplication inter-sources** (jointure EA Patriarche, ArkeoGIS ID, fuzzy commune+lieu-dit)
- Ajout d'une étape de **filtrage chronologique/géographique** configurable dans le pipeline
- Enrichissement de `config.yaml` avec les 16 nouvelles sources organisées en 2 tiers de priorité
- **BREAKING** : `pyproj`, `dbfread`, `odfpy` deviennent des dépendances optionnelles (`[rawdata]`). Prérequis système : `antiword` pour les `.doc` OLE2.

## Capabilities

### New Capabilities

- `arkeogis-extractor`: Extraction des CSV ArkeoGIS (séparateur `;`, WGS84, datation `"-620:-531"`, champs COMMENTS structurés ADAB, filtrage chrono, centroïdes)
- `patriarche-extractor`: Parsing multi-stratégie du champ compact `Identification_de_l_EA` (ordre variable, 5-8 slashs) et croisement avec `ea_fr.dbf`
- `alsace-basel-extractor`: Jointure multi-feuilles relationnelles (sites ↔ occupations ↔ mobilier), contournement bug openpyxl MultiCellRange
- `afeaf-extractor`: Extraction du fichier AFEAF avec header hiérarchique 2 niveaux (groupes + sous-colonnes)
- `tabular-extractors`: Extracteurs DBF (via `dbfread`), ODS (via `odfpy`), et enrichissement du CSVExtractor existant pour colonnes L93, booléens de période, agrégation individus→sites
- `cag-extractor`: Extraction des notices CAG — texte brut depuis `.doc` OLE2 (via `antiword`) et OCR depuis PDF scan (via Tesseract existant)
- `datation-parser`: Parser unifié pour 6 formats de datation (ArkeoGIS, texte libre, Patriarche, booléens, 14C calibré, datation textuelle Gallica) avec éclatement des fourchettes en phases individuelles
- `coordinate-reprojector`: Reprojection multi-EPSG → Lambert-93 avec cache des Transformers et détection automatique du CRS source
- `pipeline-filter`: Étape FILTER configurable dans le pipeline (filtrage chronologique âge du Fer, filtrage géographique par département/pays)

### Modified Capabilities

## Impact

- **Code** : `src/infrastructure/extractors/` (8 nouveaux fichiers + enrichissement `csv_extractor.py` et `factory.py`), `src/domain/normalizers/` (1 nouveau + enrichissement), `src/infrastructure/geocoding/` (1 nouveau), `src/application/pipeline.py` (étape FILTER)
- **Dépendances** : `pyproj>=3.6`, `dbfread>=2.0`, `odfpy>=1.4` en optional `[rawdata]` ; `antiword` en prérequis système
- **Données** : volumétrie passe de 20 sites à ~1 800–2 200 sites après déduplication
- **Configuration** : `config.yaml` enrichi avec 16 sources et options de filtrage
- **UI** : Dash et Kepler.gl afficheront automatiquement les nouveaux sites après ré-export
- **Tests** : fixtures à créer pour chaque extracteur (premières lignes des fichiers bruts)
