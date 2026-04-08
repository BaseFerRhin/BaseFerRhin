# OpenSpec — Ingestion des données brutes RawData

## Contexte

Le projet **BaseFerRhin** dispose d'un pipeline ETL existant (8 étapes `DISCOVER → EXPORT`) qui traite actuellement les sources Gallica (OCR/SRU) et un golden set CSV. Le dossier `RawData/GrosFichiers - Béhague/` contient **16 fichiers bruts** provenant de bases de données archéologiques professionnelles (ArkeoGIS, Patriarche, CAG, AFEAF, bases personnelles) qu'il faut intégrer au pipeline.

## Objectif

Créer de nouveaux extracteurs et adaptateurs pour ingérer ces 16 fichiers bruts dans le pipeline existant, en produisant des `RawRecord` normalisés puis des `Site` / `PhaseOccupation` / `Source` conformes au modèle de domaine Pydantic actuel.

---

## Décisions de périmètre

### Filtrage chronologique

Plusieurs fichiers couvrent des périodes largement hors périmètre âge du Fer :

| Fichier | Hors périmètre | Stratégie |
|---|---|---|
| `BdD_Proto_Alsace` | 646/1 127 lignes (57%) sont Bronze uniquement | Filtrer sur `BF3_HaC=1 OR HaD=1 OR LTAB=1 OR LTCD=1` → **481 sites** |
| `ADAB 2011` | 467/656 (71%) ont `STARTING_PERIOD=Indéterminé` ; 59 ont des datations Bronze ou médiévales | Exclure `STARTING_PERIOD=Indéterminé` et `ENDING_PERIOD` post-romaine → **~130 sites** |
| `necropoles` | Inclut la période BF IIIb (Bronze final) | Conserver : transition BF III → Ha C est pertinente |

**Règle** : chaque extracteur applique un filtre `is_age_du_fer()` qui conserve les sites ayant au moins une phase entre -800 et -25. Les sites exclus sont journalisés mais non ingérés.

### Filtrage géographique

| Fichier | Couverture réelle | Stratégie |
|---|---|---|
| `necropoles` | Alsace (200 sites) **+ Lorraine (139 sites)** (depts 54, 55, 57, 88) | Conserver uniquement Alsace (67, 68). Option configurable pour inclure la Lorraine |
| `ArkeoGIS Bernard` | Bade-Wurtemberg entier (DE) | Conserver : dans le périmètre Rhin supérieur |
| `ADAB 2011` | Nordbaden (DE) | Conserver : dans le périmètre Rhin supérieur |
| `habitats-tombes riches` | FR + DE + Lorraine (54, 55, 57, 88, 90) + Rhénanie-Palatinat | Filtrer sur périmètre : Alsace (67, 68) + Bade-Wurtemberg + Bâle |

### Sous-périodes composites vs modèle Pydantic

Le modèle `PhaseOccupation` valide `sous_periode` contre `_VALID_SUB_PERIODS` qui n'accepte que des valeurs simples (`Ha C`, `Ha D`, `LT A`…). Or les données brutes contiennent massivement des fourchettes (`Ha C-D`, `LT A-B`, `Ha D3-LT A1`).

**Stratégie retenue** : éclater les fourchettes en **phases distinctes** :
- `"Ha C-D"` → 2 phases : `PhaseOccupation(sous_periode="Ha C")` + `PhaseOccupation(sous_periode="Ha D")`
- `"LT A-B"` → 2 phases : `sous_periode="LT A"` + `sous_periode="LT B"`
- `"Ha D3-LT A1"` → 2 phases : `sous_periode="Ha D3"` (Periode=HALLSTATT) + `sous_periode="LT A"` (Periode=LA_TENE)
- Les dates `datation_debut`/`datation_fin` couvrent l'ensemble de la fourchette sur chaque phase

Cela préserve la validation Pydantic existante sans modifier `_VALID_SUB_PERIODS`.

### Géocodage par pays

| Pays | Service | Notes |
|---|---|---|
| FR | BAN (api-adresse.data.gouv.fr) | Existant dans le pipeline |
| DE | Nominatim (OpenStreetMap) | Existant dans le pipeline |
| CH | GeoAdmin (api3.geo.admin.ch) | Existant dans le pipeline |

Les noms de communes allemandes (ArkeoGIS, ADAB) doivent être géocodés via **Nominatim**, pas via BAN. Le multi-géocodeur existant route déjà par pays — il faut s'assurer que `Pays` est correctement renseigné dans le `RawRecord` pour le routage.

---

## Inventaire des fichiers bruts

### Priorité d'ingestion

Les fichiers sont classés en 2 tiers selon leur valeur pour la base de sites :

**Tier 1 — Sources primaires de sites** (à traiter en premier) :
- `BdD_Proto_Alsace` — base la plus complète (481 sites Fer), avec champs structurés
- `ea_fr.dbf` + `Patriarche_ageFer` — identifiants EA = clé de jointure inter-sources
- `necropoles_BFIIIb-HaD3` — 200 sites Alsace avec coordonnées L93
- `Alsace_Basel_AF` — modèle relationnel riche (sites + occupations + mobilier)
- `ArkeoGIS Bernard` + `ADAB 2011` — couverture Bade-Wurtemberg

**Tier 2 — Enrichissements thématiques** (mobilier, contexte funéraire, détail ostéologique) :
- `Inhumations silos` — données ostéologiques, ne créent pas de nouveaux sites
- `habitats-tombes riches` — mobilier de prestige, enrichit les sites existants
- `BDD-fun_AFEAF24` — pratiques funéraires, enrichit les nécropoles
- `mobilier_sepult_def.ods` — mobilier sépultures, croisement avec sites funéraires
- `CAG 67 PDF` / `CAG 68 DOC` — extraction lourde (OCR 209 MB), ROI incertain

### 1. CSV — Export ArkeoGIS (séparateur `;`, WGS84)

| Fichier | Lignes | Pertinentes (âge du Fer) | Origine | Couverture |
|---|---|---|---|---|
| `20250806_LoupBernard_ArkeoGis.csv` | 116 | 116 | Sites âge du Fer Bade-Wurtemberg (L. Bernard) | DE — enceintes, habitats |
| `20250806_ADAB2011_ArkeoGis.csv` | 656 | ~130 (après filtrage) | Inventaire archéologique Nordbaden (ADAB 2011) | DE — tous types |

**Schéma commun ArkeoGIS** (22 colonnes) :
```
SITE_AKG_ID ; DATABASE_NAME ; SITE_SOURCE_ID ; SITE_NAME ; MAIN_CITY_NAME ;
GEONAME_ID ; PROJECTION_SYSTEM (=4326) ; LONGITUDE ; LATITUDE ; ALTITUDE ;
CITY_CENTROID (Oui/Non) ; STATE_OF_KNOWLEDGE ; OCCUPATION ; STARTING_PERIOD ;
ENDING_PERIOD ; CARAC_NAME ; CARAC_LVL1 ; CARAC_LVL2 ; CARAC_LVL3 ;
CARAC_LVL4 ; CARAC_EXP ; BIBLIOGRAPHY ; COMMENTS
```

**Particularités** :
- Datation au format `"-620:-531"` (paire année début:fin) — à parser et mapper vers `Periode`/`sous_periode`
- `CARAC_LVL1` = type de site brut (`Enceinte`, `Habitat`, `Funéraire`, `Dépôt`, `Céramique`, `Métal`, `Lithique`, `Verre`, `Rituel`, `Structure agraire`…) — mapping vers `TypeSite`
- **LoupBernard : 100% des lignes ont `CITY_CENTROID=Oui`** — toutes les coordonnées sont des centroïdes de communes, aucune localisation précise. Qualité spatiale faible.
- **ADAB : 71% de périodes `Indéterminé`** — seules ~130 lignes ont une datation exploitable âge du Fer. Les 467 lignes indéterminées + 59 hors périmètre (Bronze, médiéval) sont exclues.
- `STATE_OF_KNOWLEDGE` : `Fouillé`, `Sondé`, `Littérature`, `Prospecté aérien`, `Non renseigné` → mapper vers `StatutFouille`
- `COMMENTS` du fichier ADAB contient des champs structurés allemands : `GENAUIGK_T`, `DAT_FEIN`, `TYP_FEIN` — à extraire par parsing regex
- Coordonnées en **WGS84 (EPSG:4326)** → reprojection vers **Lambert-93 (EPSG:2154)**
- Sites allemands → `Pays=DE`, géocodage via **Nominatim** (pas BAN)

### 2. Excel — Bases thématiques

| Fichier | Lignes totales | Pertinentes (âge du Fer) | Thème | Coordonnées |
|---|---|---|---|---|
| `BdD_Proto_Alsace (1).xlsx` | 1 127 | **481** | BDD proto Alsace (Bronze + Fer) | Pas de coordonnées |
| `20250806_Patriarche_ageFer.xlsx` | 836 | 836 | Base Patriarche — entités archéo âge du Fer | Pas de coordonnées |
| `Alsace_Basel_AF (1).xlsx` | Multi-feuilles | ~200 | Sites + occupations + mobilier + thésaurus | Variable (`epsg_coord`) |
| `20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx` | 339 | **200** (Alsace) | Nécropoles BF IIIb – Ha D3 | Lambert-93 |
| `20240419_Inhumations silos (1).xlsx` | 86 individus | 37 sites | Inhumations en silos (détail individu) | Lambert-93 |
| `20240425_habitats-tombes riches_Als-Lor (1).xlsx` | 110 | ~80 (après filtre géo) | Habitats et tombes riches | Pas de coordonnées |
| `BDD-fun_AFEAF24-total_04.12 (1).xlsx` | 401 | 401 | Pratiques funéraires Hallstatt (AFEAF 2024) | Pas de coordonnées |

**Détails par fichier** :

#### `BdD_Proto_Alsace` — 23 colonnes
```
id, commune, lieu_dit, EA, oa, type_oa, annee_dec, type_site, type_precision,
structures, conservati, datation_1, datation_2, rq, biblio,
BA, BM, BF1, BF2, BF3_HaC, HaD, LTAB, LTCD
```
- `type_site` : `habitat`, `funéraire`, `dépôt`, `mobilier`, `autre`, `-`
- `type_oa` : `fouille`, `diagnostic`, `prospection`, `découverte fortuite`, `surveillance de travaux`, `découverte isolée`
- Colonnes booléennes `BF3_HaC`, `HaD`, `LTAB`, `LTCD` → phases d'occupation. **Filtre : au moins 1 colonne non-null** pour retenir le site.
- `datation_1/datation_2` : texte libre (`Ha C-D`, `Bronze final`, `LT A-B`…) → normalisation
- `EA` = identifiant Patriarche → `identifiants_externes["patriarche"]` (**seulement 128/1 127 renseignés**)
- `oa` = identifiant d'opération archéologique (480/1 127 renseignés)
- **Pas de coordonnées** → géocodage par commune + lieu-dit

#### `Patriarche_ageFer` — 5 colonnes
```
Code_national_de_l_EA, Identification_de_l_EA, Numero_de_l_EA,
Nom_de_la_commune, Nom_et_ou_adresse
```
- `Identification_de_l_EA` contient en texte compact : numéro EA, code commune, commune, lieu-dit, datation, type de vestige
- **Attention : l'ordre des 2 derniers champs (datation / type) est variable** :
  - `"... / Breite / Age du bronze - Age du fer / fosse"` (lieu-dit / datation / type)
  - `"... / tumulus / Age du bronze - Age du fer"` (type / datation — inversé)
  - `"... / épingle;"` (type seul, pas de datation séparée)
- Le nombre de `/` varie : 5 slashs (5 lignes), 6 slashs (798), 7 slashs (32), 8 slashs (1). **Un regex unique ne suffira pas** — il faut un parser multi-stratégie :
  1. Splitter sur ` / `
  2. Identifier les champs fixes (positions 0-3 : n°EA, code commune, COMMUNE, vide)
  3. Classifier les champs restants par heuristique (datation si contient "Age du", "Hallstatt", "Fer", "Gallo" ; type sinon)
- `Numero_de_l_EA` au format `"67 001 0006"` → `identifiants_externes["patriarche_ea"]`
- **Pas de coordonnées** → géocodage par commune. Sert de table de référence pour relier les codes EA aux autres fichiers.

#### `Alsace_Basel_AF` — 4 feuilles
- **sites** : `id_site, pays, admin1, commune, lieu_dit, x, y, epsg_coord, decouverte_annee, ref_biblio, auteur`
- **occupations** : `id_occupation, fk_site, type, type_precision, datation, commentaire_occupation`
- **mobilier** : `id_mobilier, fk_occupation, type_mobilier, NR, NMI, quantification`
- **thésaurus** : vocabulaire contrôlé pour types et datations
- Modèle relationnel → jointure `sites ↔ occupations ↔ mobilier`
- `epsg_coord` variable → reprojection conditionnelle
- **Problème technique** : `openpyxl` plante sur ce fichier (`MultiCellRange` error sur les data validations). Solution : utiliser `pandas.read_excel()` avec `openpyxl` en mode non-readonly, ou pré-convertir en CSV avec LibreOffice CLI (`soffice --convert-to csv`).

#### `necropoles_BFIIIb-HaD3` — 37 colonnes
- Coordonnées en Lambert-93 (`Coordonnées x/y (Lambert 93)`) — **339/339 ont des coordonnées**
- Colonnes booléennes par sous-période (valeur `1` ou `-`) : `Hallstatt B2-B3 (850-800)`, `Hallstatt C1 (800-660)`, `Hallstatt C2 (660-620)`, `Hallstatt D1 (620-550)`, `Hallstatt D2 (550-500)`, `Hallstatt D3 (500-480)`
- Colonnes typologiques : `Tertre`, `Tertre arasé`, `cercle funéraire`, `Langgraben`, `Inhumation`, `crémation`, `tombe élitaire`, `tombe à armes`, `signalisation/stèle`, `Architecture tombe/bois`
- Couvre **Alsace (67, 68) + Lorraine (54, 55, 57, 88)** — filtrer sur `Dept IN (67, 68)` pour le périmètre Rhin supérieur → **200 sites**
- `TypeSite` = toujours `NECROPOLE` pour ce fichier

#### `Inhumations silos` — 94 colonnes
- Coordonnées Lambert-93 (`X(L93)`, `Y(L93)`)
- **1 individu par ligne** → **37 sites uniques** (par `Site` + `Lieu dit`)
- Données ostéologiques très détaillées (sexe, âge, pathologies, position du squelette, parure, faune)
- Datation mixte :
  - `Datation relative` : texte (`Ha D3-LT A1`, `LT C1`…)
  - `14C (2 sigma)` : fourchettes calibrées (`"780-540 avant J.C"`, `"754-411"`) → parser le format `"NNN-NNN"` ou `"NNN-NNN avant J.-C."`
- Départements : 67 et 68 (Alsace uniquement)
- **Lignes parasites** : `Département` contient `TOTAL`, `Supprimé`, `Département` (en-têtes dupliqués) → filtrer `Département IN (67, 68)`
- Stratégie d'agrégation : grouper par `(Site, Lieu dit)` → 1 `Site` avec N individus stockés dans `RawRecord.extra["individus"]`

#### `habitats-tombes riches` — 21 colonnes
- `Pays` : `D`, `F`, `f` (doublons de casse — normaliser en majuscules)
- `Dept/Land` : valeurs parasites (`Manque Tombes de Chaillon`, `Manque Tombes de Diarville`) → filtrer
- `type` : `tombe riche`, `Tombe riche`, `tombe princière`, `tombe princière ?`, `site fortifié de hauteur` — mapping :
  - `tombe riche` / `Tombe riche` / `tombe princière` / `tombe princière ?` → `NECROPOLE`
  - `site fortifié de hauteur` → `OPPIDUM`
- Mobilier de prestige : armement, or, corail, oenochoé, chaudron, situle, textile, verre → `mobilier_associe[]` ou `RawRecord.extra`
- Datation textuelle (`Datation`, `Datation globale Tum`)
- **Pas de coordonnées** → géocodage par commune + lieu-dit
- Filtrage géographique : conserver Alsace (67, 68) + Bade-Wurtemberg + Bâle

#### `BDD-fun_AFEAF24` — feuilles `PF-hallstatt` + `LISTES MENUS DEROULANTS`
- **Header hiérarchique à 2 niveaux** (pas un simple merge) :
  - Ligne 0 : groupes de colonnes (`info SITE`, `MONUMENT (enclos fossoyé)`, `MONUMENT (tumulus avéré)`, `FOSSE`, `AMENAGEMENT / CONTENANT`, `MOBILIER ASSOCIÉ AU DÉFUNT (PORTÉ)`, `DÉPÔTS d'OFFRANDE`, `REINTERVENTIONS ANTHROPIQUES`, `BIO`, `DATATION`)
  - Ligne 1 : sous-colonnes (`DPT`, `SITE`, `N° ST`, `NMI`, `N°individu`, `ENCLOS FOSSOYÉ`, `forme`…)
- Données à partir de la ligne 2 : `DPT` = département (67, 68), `SITE` = nom du site
- 63 colonnes → reconstruire les noms par concaténation `groupe.sous_colonne`
- Données funéraires détaillées : monument, fosse, mobilier, pratique funéraire → `RawRecord.extra`
- **Pas de coordonnées** → croisement avec les autres bases par commune/nom de site

### 3. ODS — Mobilier sépultures

| Fichier | Thème |
|---|---|
| `20240425_mobilier_sepult_def (1).ods` | Mobilier funéraire détaillé |

- Format OpenDocument → nécessite `odfpy` (non installé actuellement)
- **Schéma non analysé** — à explorer lors de l'implémentation après installation de `odfpy`
- Données de mobilier sépultures à croiser avec les sites funéraires (enrichissement, pas source primaire)

### 4. DBF — Shapefiles / bases dBASE

| Fichier | Lignes | Contenu |
|---|---|---|
| `ea_fr.dbf` | 42 | Entités archéologiques France (Patriarche) |
| `2026_afeaf_lineaire.dbf` | 27 | Sites linéaires AFEAF |

**`ea_fr.dbf`** — 31 champs :
```
EA_NATCODE, EA_IDENT, COMMUNE_PP, NOMUSUEL, LIEU_IGN, VESTIGES, NATURE_VES,
CHRONO_DEB, CHRONO_FIN, X_DEGRE, Y_DEGRE, SURFACE, INVENTEUR, ANNEE_DECO…
```
- Coordonnées en degrés WGS84 (`X_DEGRE`, `Y_DEGRE`) → reprojection L93
- Chronologie encodée Patriarche : `EURFER------` (âge du Fer indéterminé), `EURBRO------` (Bronze) → décoder avec table de correspondance
- `VESTIGES` : type textuel (`silo`, `fosse`…)
- `EA_NATCODE` → jointure avec `Patriarche_ageFer.Code_national_de_l_EA` et `BdD_Proto_Alsace.EA`
- Encoding : **Latin-1** (fichier dBASE allemand/français)

**`2026_afeaf_lineaire.dbf`** — 9 champs avec noms génériques (`id`, `a`, `b`, `c`, `d`, `e`, `f`, `g`, `h`) → mapping à déterminer manuellement par échantillonnage. Faible priorité (27 lignes).

### 5. Documents textuels — CAG (Carte Archéologique de la Gaule)

| Fichier | Taille | Format | Contenu |
|---|---|---|---|
| `CAG Bas-Rhin.pdf` | 209 MB | PDF scan | CAG 67 — Carte archéologique du Bas-Rhin |
| `cag_68_texte.doc` | 1.4 MB | **OLE2 .doc** | CAG 68 — texte des notices (Haut-Rhin) |
| `cag_68_biblio.doc` | 230 KB | **OLE2 .doc** | CAG 68 — bibliographie |
| `cag_68_index.doc` | 242 KB | **OLE2 .doc** | CAG 68 — index des communes |

**Attention `.doc` OLE2** : les 3 fichiers CAG 68 sont au format **Microsoft Word OLE2** (pas `.docx` Open XML). `python-docx` ne fonctionne **PAS** avec ce format. Solutions :
- **`antiword`** (outil CLI) : `antiword cag_68_texte.doc > cag_68_texte.txt` — simple, fiable
- **`textract`** (Python) : wrapper de `antiword` + autres formats
- **`olefile`** (Python) : lecture bas niveau OLE2, extraction brute du flux Word
- Recommandation : `antiword` en pré-traitement, puis parsing du texte brut

Le PDF CAG 67 (209 MB) est un scan → extraction OCR (Tesseract) via l'extracteur Gallica existant. ROI incertain : texte ancien, qualité scan variable, volumétrie élevée. À traiter en dernier.

Parsing des notices CAG (commun DOC et PDF) : chaque entrée suit le format `N° commune — Nom commune — [notices par lieu-dit]`.

---

## Mapping vers le modèle de domaine

### TypeSite (normalisation des valeurs brutes)

| Valeurs brutes (multi-sources) | → TypeSite |
|---|---|
| `Enceinte`, `oppidum`, `Oppidum`, `site fortifié de hauteur` | `OPPIDUM` |
| `Habitat`, `habitat`, `Siedlung`, `Groupé`, `Ort, Stadtbild` | `HABITAT` |
| `Funéraire`, `Nécropole`, `nécropole`, `Grabhügel`, `Bestattung`, `tombe riche`, `Tombe riche`, `tombe princière`, `tombe princière ?`, `Monument funéraire` | `NECROPOLE` |
| `Dépôt`, `dépôt` | `DEPOT` |
| `Édifice religieux`, `Rituel`, `sanctuaire` | `SANCTUAIRE` |
| `atelier`, `Réduction`, `Extraction` | `ATELIER` |
| `Voie`, `Circulation`, `Approvisionnement` | `VOIE` |
| `tumulus`, `Tertre`, `Tertre arasé` | `TUMULUS` |
| `Indéterminé`, `Autres`, `mobilier`, `-`, `Non renseigné`, vide | `INDETERMINE` |

### Periode / sous-période (parsing des datations)

**Stratégie : éclater les fourchettes composites en phases individuelles** pour respecter `_VALID_SUB_PERIODS`.

| Format brut | → Phases créées | datation_debut | datation_fin |
|---|---|---|---|
| `"-620:-531"` (ArkeoGIS) | 1 phase : HALLSTATT / Ha D | -620 | -531 |
| `"-460:-401"` | 1 phase : LA_TENE / LT A | -460 | -401 |
| `"Ha C-D"` (texte) | **2 phases** : HALLSTATT/Ha C + HALLSTATT/Ha D | -800 | -450 |
| `"LT A-B"` (texte) | **2 phases** : LA_TENE/LT A + LA_TENE/LT B | -450 | -250 |
| `"Ha D3-LT A1"` | **2 phases** : HALLSTATT/Ha D3 + LA_TENE/LT A | -480 | -400 |
| `"Bronze final/Hallstatt"` | 1 phase : HALLSTATT / null | -800 | -450 |
| `"Indéterminé"` | 1 phase : INDETERMINE / null | null | null |
| `"EURFER------"` (Patriarche) | 1 phase : INDETERMINE / null | -800 | -25 |
| `"Age du bronze - Age du fer"` | 1 phase : TRANSITION / null | -800 | -450 |
| `"Age du fer - Gallo-romain"` | 1 phase : LA_TENE / null | -450 | -25 |
| Colonnes booléennes `HaD=1, LTAB=1` | **2 phases** : HALLSTATT/Ha D + LA_TENE/LT A + LA_TENE/LT B | — | — |
| `"780-540 avant J.C"` (14C) | 1 phase : déduite des bornes calibrées | -780 | -540 |

### StatutFouille (mapping)

| Valeur brute | → StatutFouille |
|---|---|
| `Fouillé`, `fouille` | `FOUILLE` |
| `Sondé`, `diagnostic` | `FOUILLE` |
| `Prospecté aérien`, `prospection` | `PROSPECTION` |
| `Littérature`, `découverte fortuite`, `découverte isolée` | `SIGNALEMENT` |
| `surveillance de travaux` | `PROSPECTION` |
| `Non renseigné` | `null` |

### PrecisionLocalisation

| Condition | → PrecisionLocalisation |
|---|---|
| `CITY_CENTROID=Oui` (100% de LoupBernard, partie d'ADAB) | `centroïde` |
| Coordonnées absentes → géocodées par commune | `centroïde` |
| `GENAUIGK_T : mit 20 m Toleranz` (ADAB) | `exact` |
| `GENAUIGK_T : mit Ungenauigkeit bis zu 200m` (ADAB) | `approx` |
| Coordonnées Lambert-93 fournies (necropoles, silos) | `exact` |

### Reprojection des coordonnées

| Source | EPSG source | Action |
|---|---|---|
| ArkeoGIS CSV | 4326 (WGS84) | `pyproj.Transformer(4326 → 2154)` |
| ea_fr.dbf | 4326 (degrés) | `pyproj.Transformer(4326 → 2154)` |
| Alsace_Basel_AF | Variable (`epsg_coord`) | Reprojection conditionnelle |
| necropoles / silos | 2154 (Lambert-93) | Aucune — déjà en L93 |
| Fichiers sans coordonnées | — | Géocodage BAN (FR) / Nominatim (DE) / GeoAdmin (CH) → L93 |

---

## Architecture technique proposée

### Nouveaux extracteurs (`src/infrastructure/extractors/`)

```
src/infrastructure/extractors/
├── base.py                    # Protocol SourceExtractor (existant)
├── csv_extractor.py           # CSV/XLSX générique (existant, à enrichir)
├── arkeogis_extractor.py      # NEW — CSV ArkeoGIS avec parsing datation
├── dbf_extractor.py           # NEW — Fichiers dBASE (.dbf) via dbfread
├── ods_extractor.py           # NEW — OpenDocument Spreadsheet (.ods) via odfpy
├── doc_extractor.py           # NEW — Microsoft Word OLE2 (.doc) via antiword
├── patriarche_extractor.py    # NEW — Parsing multi-stratégie Patriarche
├── cag_notice_extractor.py    # NEW — Parsing notices CAG (texte brut)
├── alsace_basel_extractor.py  # NEW — Multi-feuilles relationnelles (jointure)
├── afeaf_extractor.py         # NEW — Header hiérarchique 2 niveaux AFEAF
└── factory.py                 # Factory (existant, à enrichir)
```

### Nouveau normaliseur de datation (`src/domain/normalizers/`)

```
src/domain/normalizers/
├── period_normalizer.py       # Existant — à enrichir
└── datation_parser.py         # NEW — Parse "-620:-531", "Ha C-D", "EURFER",
                               #   booléens, 14C calibré, "Age du fer - Gallo-romain"
                               #   Éclate les fourchettes en phases individuelles
```

### Nouveau module de reprojection (`src/infrastructure/geocoding/`)

```
src/infrastructure/geocoding/
├── reprojector.py             # NEW — Reprojection multi-EPSG → Lambert-93 (pyproj)
└── ...                        #   Cache des Transformers, détection auto EPSG
```

### Configuration (`config.yaml`)

```yaml
sources:
  - path: data/sources/golden_sites.csv
    type: csv

  # --- Tier 1 : Sources primaires ---
  - path: RawData/GrosFichiers - Béhague/BdD_Proto_Alsace (1).xlsx
    type: xlsx
    origin: "BdD Proto Alsace"
    filter_age_du_fer: true
    column_mapping:
      commune: commune
      lieu_dit: lieu_dit
      type_site: type_mention
      datation_1: periode_mention

  - path: RawData/GrosFichiers - Béhague/ea_fr.dbf
    type: dbf
    origin: "Patriarche — EA France"

  - path: RawData/GrosFichiers - Béhague/20250806_Patriarche_ageFer.xlsx
    type: patriarche
    origin: "Patriarche — âge du Fer"

  - path: RawData/GrosFichiers - Béhague/20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx
    type: xlsx
    origin: "Nécropoles BFIIIb-HaD3"
    filter_departments: [67, 68]
    column_mapping:
      Commune: commune
      Coordonnées x (Lambert 93): x_l93
      Coordonnées y (Lambert 93): y_l93

  - path: RawData/GrosFichiers - Béhague/Alsace_Basel_AF (1).xlsx
    type: alsace_basel
    origin: "Alsace-Basel AF"

  - path: RawData/GrosFichiers - Béhague/20250806_LoupBernard_ArkeoGis.csv
    type: arkeogis
    origin: "Bernard — Bade-Wurtemberg"
    pays: DE

  - path: RawData/GrosFichiers - Béhague/20250806_ADAB2011_ArkeoGis.csv
    type: arkeogis
    origin: "ADAB 2011 — Nordbaden"
    pays: DE
    filter_age_du_fer: true

  # --- Tier 2 : Enrichissements ---
  - path: RawData/GrosFichiers - Béhague/20240419_Inhumations silos (1).xlsx
    type: xlsx
    origin: "Inhumations silos"
    aggregate_by: [Site, Lieu dit]
    column_mapping:
      Site: commune
      Lieu dit: lieu_dit
      X(L93): x_l93
      Y(L93): y_l93

  - path: RawData/GrosFichiers - Béhague/20240425_habitats-tombes riches_Als-Lor (1).xlsx
    type: xlsx
    origin: "Habitats-tombes riches"
    filter_perimeter: true

  - path: RawData/GrosFichiers - Béhague/BDD-fun_AFEAF24-total_04.12 (1).xlsx
    type: afeaf
    origin: "AFEAF 2024 — funéraire Hallstatt"

  - path: RawData/GrosFichiers - Béhague/20240425_mobilier_sepult_def (1).ods
    type: ods
    origin: "Mobilier sépultures"

  - path: RawData/GrosFichiers - Béhague/2026_afeaf_lineaire.dbf
    type: dbf
    origin: "AFEAF linéaire"

  - path: RawData/GrosFichiers - Béhague/cag_68_texte.doc
    type: cag_doc
    origin: "CAG 68 — Haut-Rhin"

  - path: RawData/GrosFichiers - Béhague/CAG Bas-Rhin.pdf
    type: cag_pdf
    origin: "CAG 67 — Bas-Rhin (scan OCR)"
```

---

## Dépendances à ajouter

```toml
[project.optional-dependencies]
rawdata = [
    "pyproj>=3.6",       # reprojection EPSG
    "dbfread>=2.0",      # lecture .dbf
    "odfpy>=1.4",        # lecture .ods via pandas
]
```

Prérequis système :
- **`antiword`** : extraction texte des `.doc` OLE2 (`brew install antiword` / `apt install antiword`)

---

## Plan d'implémentation (Epics)

### Epic 1 — Extracteurs Tier 1 (sources primaires)

**Feature 1.1** : `ArkeoGISExtractor` — parse les 2 CSV ArkeoGIS
- Parser le format de datation `"-620:-531"` en `datation_debut`/`datation_fin`
- Mapper `CARAC_LVL1` → `TypeSite`
- Extraire les champs structurés du champ `COMMENTS` (ADAB) via regex sur `GENAUIGK_T`, `DAT_FEIN`, `TYP_FEIN`
- Reprojeter WGS84 → Lambert-93
- Attribuer `precision_localisation` selon `CITY_CENTROID` et `GENAUIGK_T`
- Filtrer les sites hors périmètre chronologique (ADAB : exclure `Indéterminé` et post-romains)
- Renseigner `Pays=DE` pour le routage géocodeur

**Feature 1.2** : `PatriarcheExtractor` — parser multi-stratégie `Identification_de_l_EA`
- Splitter sur ` / `, identifier les champs fixes (positions 0-3)
- Classifier les champs variables par heuristique (datation vs type de vestige)
- Gérer les cas à 5, 6, 7 ou 8 slashs
- Croiser avec `ea_fr.dbf` pour récupérer les coordonnées WGS84 via `EA_NATCODE`

**Feature 1.3** : `AlsaceBaselExtractor` — jointure multi-feuilles
- Contourner le bug `openpyxl` (`MultiCellRange`) : lire via `pandas.read_excel()` ou pré-convertir
- Lire les 4 feuilles (`sites`, `occupations`, `mobilier`, `thésaurus`)
- Joindre `sites ↔ occupations` (FK) pour produire des `RawRecord` avec phases
- Reprojection conditionnelle selon `epsg_coord`

**Feature 1.4** : Enrichir `CSVExtractor` existant pour les XLSX thématiques
- Supporter les colonnes Lambert-93 (`X(L93)`, `Y(L93)`)
- Agréger les lignes par site (Inhumations silos : 37 sites uniques depuis 86 individus)
- Parser les colonnes booléennes de période (`BF3_HaC`, `HaD`, `LTAB`, `LTCD`) → éclater en phases
- Filtrer `BdD_Proto_Alsace` sur les colonnes booléennes Fer (retenir 481/1 127)
- Filtrer les lignes parasites (Inhumations silos : `Département` = `TOTAL`, `Supprimé`)
- Normaliser les `Pays` (`f` → `F` → `FR`, `D` → `DE`)

**Feature 1.5** : `DBFExtractor` — lecture dBASE via `dbfread`
- Mapper les champs `ea_fr.dbf` (31 champs) vers `RawRecord`
- Décoder les chronologies Patriarche (`EURFER------`, `EURBRO------`)
- Encoding Latin-1

### Epic 2 — Extracteurs Tier 2 (enrichissements)

**Feature 2.1** : `AFEAFExtractor` — header hiérarchique 2 niveaux
- Lire lignes 0-1 comme groupes + sous-colonnes
- Reconstruire les noms de colonnes par concaténation `{groupe}.{sous_colonne}`
- `DPT` et `SITE` identifient le site → croisement avec les bases Tier 1
- Extraire les données funéraires comme `mobilier_associe[]` et `RawRecord.extra`

**Feature 2.2** : `ODSExtractor` — lecture OpenDocument via `odfpy`/pandas
- À détailler après exploration du schéma (nécessite installation `odfpy`)

**Feature 2.3** : Nettoyage `habitats-tombes riches`
- Normaliser `Pays` (`f` → `FR`, `D` → `DE`)
- Filtrer `Dept/Land` parasites (`Manque Tombes de...`)
- Mapper `type` complet (`tombe princière` → `NECROPOLE`, `site fortifié de hauteur` → `OPPIDUM`)
- Filtrage géographique configurable

### Epic 3 — Extraction documentaire (DOC, PDF)

**Feature 3.1** : `CAGDocExtractor` — parsing notices CAG 68 (.doc OLE2)
- Pré-extraction texte via `antiword` (pas `python-docx` — incompatible OLE2)
- Parser le texte brut notice par notice
- Identifier les entrées par commune → vestiges → datation → bibliographie
- Séparer `cag_68_texte.doc` (notices), `cag_68_index.doc` (index communes), `cag_68_biblio.doc` (références)

**Feature 3.2** : `CAGPdfExtractor` — OCR du scan CAG 67 (209 MB)
- Réutiliser le pipeline OCR Tesseract/Gallica existant
- Découper le PDF en pages, OCR par page
- Même parsing de notices que Feature 3.1
- **Basse priorité** : ROI incertain, qualité OCR sur texte ancien variable

### Epic 4 — Normalisation et reprojection

**Feature 4.1** : `DatationParser` — normalisation unifiée des datations
- Format ArkeoGIS : `"-620:-531"` → dates absolues
- Format texte : `"Ha C-D"`, `"LT A-B"` → **éclater en phases individuelles** conformes à `_VALID_SUB_PERIODS`
- Format Patriarche : `"EURFER------"`, `"Age du bronze - Age du fer"`, `"Age du fer - Gallo-romain"` → Periode + bornes larges
- Format booléen : colonnes `HaD=1` → phase `Ha D`
- Format 14C calibré : `"780-540 avant J.C"`, `"754-411"` → bornes numériques
- Table de correspondance sous-période → dates estimées (consensus chronologique)

**Feature 4.2** : `Reprojector` — reprojection multi-EPSG vers Lambert-93
- Détection automatique du CRS source (4326, 2154, 3857, ou via `epsg_coord`)
- Transformation `pyproj` avec cache des transformers
- Validation des bornes L93 après reprojection (cross-check avec `_X_L93_MIN/MAX`)

**Feature 4.3** : Enrichir le `TypeNormalizer` existant
- Ajouter les valeurs allemandes (`Siedlung`, `Grabhügel`, `Bestattung`, `Ort, Stadtbild`)
- Ajouter les valeurs du fichier habitats-tombes riches (`tombe princière`, `site fortifié de hauteur`)
- Normaliser la casse et les accents

### Epic 5 — Déduplication inter-sources

**Feature 5.1** : Enrichir le scoring de déduplication
- Croiser par code EA Patriarche (`identifiants_externes["patriarche_ea"]`) — jointure exacte
- Croiser par `SITE_AKG_ID` (ArkeoGIS) — jointure exacte
- Croiser par commune + lieu-dit + type (scoring fuzzy existant)
- Fusionner les métadonnées complémentaires (mobilier, bibliographie, coordonnées)
- Privilégier les coordonnées exactes sur les centroïdes lors du merge

### Epic 6 — Intégration pipeline

**Feature 6.1** : Mettre à jour `config.yaml` avec les nouvelles sources (Tier 1 puis Tier 2)
**Feature 6.2** : Mettre à jour `factory.py` pour instancier les nouveaux extracteurs
**Feature 6.3** : Ajouter une étape `FILTER` optionnelle dans le pipeline (filtrage chrono/géo)
**Feature 6.4** : Tests unitaires par extracteur (fixtures = premières lignes de chaque fichier)
**Feature 6.5** : Recalculer les statistiques globales et mettre à jour la UI Dash + Kepler.gl

---

## Volumétrie attendue

| Source | Lignes brutes | Pertinentes (âge du Fer + périmètre) | Après dédup (estimé) |
|---|---|---|---|
| Golden set (existant) | 20 | 20 | 20 |
| ArkeoGIS Bernard | 116 | 116 (tous centroïdes) | ~100 |
| ArkeoGIS ADAB | 656 | **~130** (71% Indéterminé exclus) | ~100 |
| BdD Proto Alsace | 1 127 | **481** (57% Bronze exclus) | ~350 |
| Patriarche | 836 | 836 | ~500 |
| Alsace Basel AF | ~200 | ~200 | ~150 |
| Nécropoles | 339 | **200** (Alsace uniquement) | ~180 |
| Inhumations silos | 86 (individus) | **37 sites** | ~30 |
| Habitats-tombes riches | 110 | **~80** (filtre géo) | ~60 |
| AFEAF funéraire | 401 | 401 | ~300 (enrichissements) |
| ea_fr.dbf | 42 | 42 | ~35 |
| CAG 68 DOC | ~500 (estimé) | ~400 | ~300 |
| CAG 67 PDF | ~1 000 (estimé) | ~800 | ~500 |
| **Total** | **~5 400** | **~3 750** | **~1 800 – 2 200** |

---

## Contraintes

1. **Clean Architecture** — les extracteurs restent dans `infrastructure/`, le mapping domaine dans `domain/normalizers/`
2. **Pas de perte de données** — tout champ non mappé va dans `RawRecord.extra`
3. **Traçabilité** — chaque `Source` référence le fichier d'origine, la base source et la méthode d'extraction
4. **Idempotence** — réexécuter le pipeline ne duplique pas les sites
5. **Encoding** — supporter UTF-8, Latin-1, CP1252 (fichiers allemands)
6. **Fichiers volumineux** — le PDF CAG 67 (209 MB) doit être traité par chunks/pages
7. **Qualité** — tests unitaires avec fixtures extraites des premières lignes de chaque fichier
8. **Validation Pydantic** — les sous-périodes produites doivent être dans `_VALID_SUB_PERIODS` (éclater les fourchettes)
9. **Filtrage explicite** — journaliser les lignes exclues (hors périmètre chrono/géo) pour traçabilité
10. **Format `.doc` OLE2** — utiliser `antiword` (pas `python-docx`) pour les CAG 68
