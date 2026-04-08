# Sources de données

Catalogue des 16 sources ingérées par le pipeline, organisées en Tier 1 (primaires) et Tier 2 (enrichissement).

## Vue d'ensemble

```
16 sources → 2 007 records (après filtre) → 1 589 sites → 503 sites uniques
```

| Tier | Sources | Formats | Extracteurs |
|------|---------|---------|-------------|
| Tier 1 | 9 | CSV, XLSX, DBF | ArkeoGIS, Patriarche, Alsace-Basel, thématiques |
| Tier 2 | 7 | XLSX, DBF, ODS, DOC, OCR | AFEAF, CAG, Gallica, mobilier |

## Tier 1 — Sources primaires

### ArkeoGIS LoupBernard (Bade-Wurtemberg)

| Propriété | Valeur |
|---|---|
| Fichier | `20250806_LoupBernard_ArkeoGis.csv` |
| Type config | `arkeogis` |
| Extracteur | `ArkeoGISExtractor` |
| Format | CSV délimité `;`, encodage UTF-8 ou Latin-1 |
| Champs clés | `SITE_AKG_ID`, `SITE_NAME`, `MAIN_CITY_NAME`, `LATITUDE`, `LONGITUDE`, `STARTING_PERIOD`, `ENDING_PERIOD`, `CARAC_LVL1`, `DATABASE_NAME`, `COMMENTS` |
| Particularités | Détection automatique `pays=DE` depuis `DATABASE_NAME` (ADAB, Baden, Wurtemberg). Précision localisation depuis `CITY_CENTROID` et `COMMENTS`. Parsing dates au format `"-800:-450"`. |

### ArkeoGIS ADAB 2011 (Nordbaden)

| Propriété | Valeur |
|---|---|
| Fichier | `20250806_ADAB2011_ArkeoGis.csv` |
| Type config | `arkeogis` |
| Options | `filter_age_du_fer: true` |
| Particularités | Filtre exclusion : `STARTING_PERIOD = Indéterminé` seul, dates post-romaines (fin > 500). Même extracteur que LoupBernard. |

### Patriarche DRAC

| Propriété | Valeur |
|---|---|
| Fichier | `20250806_Patriarche_ageFer.xlsx` |
| Type config | `patriarche` |
| Options | `dbf_path: ea_fr.dbf` |
| Extracteur | `PatriarcheExtractor` |
| Champs clés | `Identification_de_l_EA` (format compact : id / code / commune / / lieu-dit / …), `Numero_de_l_EA`, `Code_national_de_l_EA`, `Nom_de_la_commune` |
| Croisement DBF | `ea_fr.dbf` fournit coordonnées (`X_DEGRE`, `Y_DEGRE`) et chrono (`CHRONO`/`EUR_PERIODE`). Encodage cp1252. Codes EUR décodés (EURFER → Âge du Fer, etc.). |
| Parsing | Champ `Identification_de_l_EA` découpé par ` / `, heuristiques regex pour distinguer type/datation dans les segments tail. |

### ea_fr.dbf (coordonnées Patriarche)

| Propriété | Valeur |
|---|---|
| Fichier | `ea_fr.dbf` |
| Type config | `dbf` |
| Extracteur | `DBFExtractor` |
| Options | `column_mapping: {COMMUNE_PP: commune, VESTIGES: type_mention, X_DEGRE: longitude_raw, Y_DEGRE: latitude_raw}` |
| Encodage | cp1252 (corrigé depuis latin-1) |

### Alsace-Basel (base relationnelle)

| Propriété | Valeur |
|---|---|
| Fichier | `Alsace_Basel_AF (1).xlsx` |
| Type config | `alsace_basel` |
| Extracteur | `AlsaceBaselExtractor` |
| Structure | 4 feuilles : `sites` (id, commune, pays, coords, EPSG), `occupations` (site FK, type, datation), `mobilier` (occ FK, matériau), `thésaurus` (codes → labels) |
| Particularités | Reprojection conditionnelle selon `epsg_coord` (4326 → WGS84 lat/lon, 2154 → L93 direct, autre → `Reprojector`). Patch openpyxl pour `MultiCellRange` bug. Thésaurus en colonnes positionnelles (doublons de noms). |

### BdD Proto Alsace

| Propriété | Valeur |
|---|---|
| Fichier | `BdD_Proto_Alsace (1).xlsx` |
| Type config | `bdd_proto_alsace` |
| Extracteur | `BdDProtoAlsaceExtractor` |
| Logique | Colonnes booléennes `BF3_HaC`, `HaD`, `LTAB`, `LTCD` — un site est retenu s'il a au moins une colonne âge du Fer non vide/non nulle. Champs : `commune`, `lieu_dit`, `type_site`, `datation_1`, `EA`. |

### Nécropoles BFIIIb-HaD3 Alsace-Lorraine

| Propriété | Valeur |
|---|---|
| Fichier | `20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx` |
| Type config | `necropoles` |
| Options | `filter_departments: [67, 68]` |
| Extracteur | `NecropoleExtractor` |
| Champs | `Dept`, `Commune`, `Nom`, `Datation`, `Coordonnées x/y (Lambert 93)` |
| Particularités | Coordonnées nativement en Lambert-93 (stockées dans `extra["x_l93"]`/`extra["y_l93"]`). Filtre par département. |

### Inhumations en silos

| Propriété | Valeur |
|---|---|
| Fichier | `20240419_Inhumations silos (1).xlsx` |
| Type config | `inhumations_silos` |
| Extracteur | `InhumationsSilosExtractor` |
| Logique | Données individuelles agrégées par clé `commune|lieu_dit` → 1 record par site avec `individus_count`. Coords Lambert-93 depuis `X(L93)`/`Y(L93)`. Datation 14C parsée (regex `(\d+)\s*[-–]\s*(\d+)`). Exclusion des lignes parasites (TOTAL, Supprimé...). |

### Habitats-tombes riches Alsace-Lorraine

| Propriété | Valeur |
|---|---|
| Fichier | `20240425_habitats-tombes riches_Als-Lor (1).xlsx` |
| Type config | `habitats_tombes_riches` |
| Options | `filter_departments: [67, 68]` (effectif) |
| Extracteur | `HabitatsTombesRichesExtractor` |
| Champs | `Pays`, `Dept/Land`, `Commune`, `Lieudit`, `type` |
| Particularités | Normalisation pays (f→FR, d→DE, ch→CH, s→CH). Mapping type riche → type normalisé (tombe princière → nécropole, site fortifié → oppidum…). |

## Tier 2 — Enrichissement

### AFEAF funéraire

| Propriété | Valeur |
|---|---|
| Fichier | `BDD-fun_AFEAF24-total_04.12 (1).xlsx` |
| Type config | `afeaf` |
| Extracteur | `AFEAFExtractor` |
| Particularités | Header hiérarchique à 2 niveaux (ligne 1 = catégorie, ligne 2 = sous-champ). Reconstruction automatique en `catégorie__sous_champ`. Données funéraires avec type systématiquement « nécropole ». Département extrait du champ reconstruit. |

### AFEAF linéaire

| Propriété | Valeur |
|---|---|
| Fichier | `2026_afeaf_lineaire.dbf` |
| Type config | `dbf` |
| Extracteur | `DBFExtractor` |

### Mobilier sépultures (ODS)

| Propriété | Valeur |
|---|---|
| Fichier | `20240425_mobilier_sepult_def (1).ods` |
| Type config | `ods` |
| Extracteur | `ODSExtractor` |
| Dépendance | `odfpy>=1.4` |
| Format | Spreadsheet OpenDocument. Lecture via `pd.read_excel(engine='odf')`. |

### CAG 68 texte (notices)

| Propriété | Valeur |
|---|---|
| Fichier | `cag_68_texte.doc` |
| Type config | `cag_doc` |
| Options | `source_label: cag_68` |
| Extracteur | `_CAGDocExtractor` → `DocExtractor` + `CAGNoticeExtractor` |
| Logique | 1. `DocExtractor` extrait le texte via `antiword` (subprocess). 2. `CAGNoticeExtractor` découpe par commune (regex `^NNN — COMMUNE`), puis par sous-notice lieu-dit (regex `(NNN AA)`). 3. Extraction datation et vestiges par regex. 4. Classification type par vestiges détectés. |
| Dépendance | `antiword` (binaire système) |

### CAG 68 index / bibliographie

| Propriété | Valeur |
|---|---|
| Fichiers | `cag_68_index.doc`, `cag_68_biblio.doc` |
| Type config | `doc` |
| Extracteur | `DocExtractor` |

### Gallica (BnF)

| Propriété | Valeur |
|---|---|
| Type config | via `gallica_queries` dans config.yaml |
| Extracteur | `GallicaExtractor` (orchestrateur async) |
| Composants | `GallicaSRUClient` (recherche), `GallicaIIIFClient` (images), `TesseractOCRClient` (OCR fra+deu), `GallicaOCRClient` (texteBrut fallback), `OCRQualityScorer`, `GallicaSiteMentionExtractor` (regex communes/types) |
| Stratégie | SRU → pages IIIF → Tesseract local → fallback texteBrut. Cache disque par page. Sémaphore 2 connexions. Scoring qualité OCR sur lexique français. |

### Golden set

| Propriété | Valeur |
|---|---|
| Fichier | `data/sources/golden_sites.csv` |
| Type config | `csv` |
| Extracteur | `CSVExtractor` |
| Rôle | 20 sites de référence validés manuellement pour tests de régression. |

## Champs `extra` par extracteur

Le champ `extra` du `RawRecord` transporte des métadonnées spécifiques :

| Extracteur | Clés `extra` principales |
|---|---|
| ArkeoGIS | `SITE_AKG_ID`, `DATABASE_NAME`, `precision_localisation`, `datation_debut`, `datation_fin`, `pays` |
| Patriarche | `patriarche_ea`, `patriarche_code_national`, `lieu_dit`, `chrono_dbf` |
| Alsace-Basel | `id_site`, `pays`, `admin1`, `occupations`, `epsg_source`, `x_l93`/`y_l93`, `lieu_dit` |
| BdD Proto | `phases_bool` (liste des colonnes Fer actives), `EA`, `lieu_dit` |
| Nécropoles | `lieu_dit`, `x_l93`/`y_l93`, `epsg_source` |
| Inhumations | `individus_count`, `lieu_dit`, `x_l93`/`y_l93`, `datation_14c_debut`/`fin` |
| Habitats riches | `pays`, `dept_land`, `lieu_dit` |
| AFEAF | `departement`, colonnes reconstruites, `funeraire_*` |
| CAG notices | `cag_commune_id`, `lieu_dit`, `datation_mentions`, `vestiges_mentions`, `bibliographie` |
| Gallica | `ark_id`, `confiance_ocr`, `page_number` |

## Configuration des sources (`config.yaml`)

```yaml
sources:
  # Tier 1
  - path: "RawData/GrosFichiers - Béhague/20250806_LoupBernard_ArkeoGis.csv"
    type: arkeogis
  - path: "RawData/GrosFichiers - Béhague/20250806_ADAB2011_ArkeoGis.csv"
    type: arkeogis
    options:
      filter_age_du_fer: true
  - path: "RawData/GrosFichiers - Béhague/20250806_Patriarche_ageFer.xlsx"
    type: patriarche
    options:
      dbf_path: "RawData/GrosFichiers - Béhague/ea_fr.dbf"
  # ... (16 sources au total)

filter:
  chrono: true
  departments: [67, 68]
```

Modèle Pydantic : `PipelineConfig` + `FilterConfig` dans `src/application/config.py`.
