# Analyse du jeu de données ArkeoGIS — Loup Bernard (Bade-Wurtemberg)

**Fichier analysé :** `20250806_LoupBernard_ArkeoGis.csv`  
**Emplacement dans le dépôt :** `data/input/20250806_LoupBernard_ArkeoGis.csv` (copie de travail pour l’ingestion ; ce dossier `data/analysis/...` documente l’export).

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Source** | Export ArkeoGIS — base « Sites de l'âge du Fer dans le Bade-Wurtemberg - Bernard » (Loup Bernard) |
| **Volume** | 116 lignes, 23 colonnes |
| **Sites distincts** | 105 identifiants `SITE_AKG_ID` uniques (99 noms de site distincts côté `SITE_NAME`, liés aux micro-toponymes répétés) |
| **Format** | CSV, séparateur `;`, encodage UTF-8 |
| **Référence spatiale** | EPSG:4326 (WGS84), champ `PROJECTION_SYSTEM` = `4326` |
| **Emprise** | Land de **Bade-Württemberg** (Allemagne) — lat. **47,58–49,20° N**, long. **7,52–10,47° E** |
| **Chronologie** | Âge du Fer uniquement : plages numériques en années négatives (avant notre ère), **116/116** lignes avec `STARTING_PERIOD` et `ENDING_PERIOD` renseignés (**0** indéterminé au sens « vide ») |
| **Localisation** | **100 %** des points marqués **centroïde communal** (`CITY_CENTROID` = « Oui » pour toutes les lignes) |
| **Bibliographie** | Très dense : **115/116** lignes avec `BIBLIOGRAPHY` non vide (**≈ 99,1 %**) |
| **Qualité globale** | **Élevée** pour un export tabulaire : pas de doublons de ligne complète, champs structurants remplis, hiérarchie CARAC cohérente ; la principale limite est **géométrique** (centroïdes) et **documentaire** (littérature allemande, biais thématique des enceintes) |

---

## 2. Schéma détaillé des colonnes

Types indiqués au sens logique (données lues comme texte dans le CSV). Les **valeurs dominantes** résument les modalités les plus fréquentes sur les 116 lignes.

| Colonne | Type logique | Remplissage | Valeurs uniques | Valeurs dominantes (fréquence) |
|---------|----------------|-------------|-----------------|--------------------------------|
| `SITE_AKG_ID` | entier (texte) | 100 % | 105 | un ID par site ; max **12** lignes pour le site **25833** (Schlossberg / Neuenbürg) |
| `DATABASE_NAME` | texte | 100 % | 1 | « Sites de l'âge du Fer dans le Bade-Wurtemberg - Bernard » (116) |
| `SITE_SOURCE_ID` | entier (texte) | 100 % | 105 | identifiant source interne ; corrélation 1:1 avec le grain site (hors éclatement mobilier) |
| `SITE_NAME` | texte | 100 % | 99 | micro-toponyme (ex. Schlossberg ×14, Lemberg ×3, Kirchberg ×2…) |
| `MAIN_CITY_NAME` | texte | 100 % | 100 | commune allemande rattachée au centroïde (ex. Neuenbürg ×12) |
| `GEONAME_ID` | texte | **0 %** | 0 | colonne vide dans cet export |
| `PROJECTION_SYSTEM` | entier (texte) | 100 % | 1 | `4326` (116) |
| `LONGITUDE` | décimal WGS84 | 100 % | 68 | répartition sur le BW (plusieurs sites partagent un même centroïde communal) |
| `LATITUDE` | décimal WGS84 | 100 % | 61 | idem |
| `ALTITUDE` | entier (texte) | 100 % | 71 | dont `0` pour une part des entrées (valeur sentinelle ou non renseignée côté source) |
| `CITY_CENTROID` | booléen texte | 100 % | 1 | « Oui » (116) |
| `STATE_OF_KNOWLEDGE` | texte | 100 % | 4 | Fouillé (46), Littérature (36), Sondé (22), Non renseigné (12) |
| `OCCUPATION` | texte | 100 % | 4 | Multiple (63), Non renseigné (47), Unique (4), Continue (2) |
| `STARTING_PERIOD` | plage texte | 100 % | 8 | plages du type `-620:-531`, `-800:-26`, etc. |
| `ENDING_PERIOD` | plage texte | 100 % | 7 | idem |
| `CARAC_NAME` | texte | 100 % | 3 | Immobilier (107), Mobilier (8), Production (1) |
| `CARAC_LVL1` | texte | 100 % | 7 | Enceinte (105), Métal (6), Céramique, Verre, Lithique, Habitat, Dépôt (1 chacun) |
| `CARAC_LVL2` | texte | **8,6 %** | 7 | sinon vide ; Outils (3), Parure (3), Vaisselle, Autres, Forge (1) |
| `CARAC_LVL3` | texte | **7,8 %** | 10 | détail mobilier (Hache, Fibule, Perle…) |
| `CARAC_LVL4` | texte | **1,7 %** | 3 | très rare (Bracelet, Import…) |
| `CARAC_EXP` | texte | 100 % | 2 | Non (107), Oui (9) |
| `BIBLIOGRAPHY` | texte | **99,1 %** | 108 | références allemandes (KBW, FBS, monographies type Biel 1987, Rieckhoff 2001, Archäologische Ausgrabungen BW…) ; **1** ligne sans référence |
| `COMMENTS` | texte | **44,0 %** | 50 | notes DE/FR (fossés, tessons, questions de culte, renvois aux plans KBW…) |

---

## 3. Analyse du modèle de données

### 3.1 Grain « multi-lignes » ArkeoGIS

Dans cet export, **une ligne ne correspond pas toujours à un site unique** : le couple (`SITE_AKG_ID`, période, caractérisation) peut se répéter pour détailler **plusieurs facettes** du même lieu (mobilier, production, sous-ensembles de l’enceinte). On observe en moyenne **≈ 1,1 ligne par site** (116 / 105). Le cas extrême **Schlossberg (Neuenbürg)** atteint **12 lignes** : fort détail mobilier et bibliographique pour une **série d’interventions** sur un même oppidum / établissement fortifié.

### 3.2 Arbre CARAC (observé sur ce fichier)

La hiérarchie suit la logique ArkeoGIS : **`CARAC_NAME`** (nature de l’information) → **`CARAC_LVL1`** (grand domaine) → **`CARAC_LVL2`** → **`CARAC_LVL3`** → **`CARAC_LVL4`**, avec explication booléenne **`CARAC_EXP`** (explicite / non).

- **Niveau 1 — `CARAC_NAME`**  
  - **Immobilier** (dominant) : structures, enceintes, occupation spatiale.  
  - **Mobilier** : objets (métal, céramique, verre, parure…).  
  - **Production** : trace ponctuelle de zone de production (1 ligne).

- **Niveau 2 — `CARAC_LVL1`** (toujours renseigné ici)  
  - **Enceinte** (~**90 %** des lignes) : aligné avec l’objectif documentaire de la base (inventaire d’**enceintes** et sites analogues du BW).  
  - **Métal**, **Céramique**, **Verre**, **Lithique** : branches mobilier.  
  - **Habitat**, **Dépôt** : exceptions rares mais typologiquement importantes pour le mapping vers `TypeSite`.

- **Niveaux 3–4** : majoritairement **vides** (**≈ 91,4 %** de `CARAC_LVL2` vide, **≈ 92 %** pour `CARAC_LVL3`/`CARAC_LVL4` combinés dans la pratique). Lorsqu’ils sont présents, on retrouve des catégories du type **Outils**, **Parure**, **Vaisselle**, **Forge**, avec des précisions (Hache, Fibule…).

### 3.3 Chronologie dans le fichier

Les champs `STARTING_PERIOD` et `ENDING_PERIOD` utilisent des **intervalles textuels** `borne_inf:borne_sup` (entiers négatifs). Ils se prêtent à une conversion en **`datation_debut` / `datation_fin`** entières pour le domaine BaseFerRhin, puis à un **recoupement** avec les fenêtres **Hallstatt** / **La Tène** / **Transition** définies dans `data/reference/periodes.json` (voir section 5).

### 3.4 Occupation et état des connaissances

- **`OCCUPATION`** décrit la **courbe d’occupation** (multiple, unique, continue) au niveau sémantique « synthèse » ; beaucoup de **Non renseigné**.  
- **`STATE_OF_KNOWLEDGE`** distingue **fouille**, **sondage**, **littérature** et **non renseigné** — utile pour le **`statut_fouille`** et le **commentaire qualité** côté agrégat `Site`.

---

## 4. Analyse de qualité

| Critère | Constat |
|---------|---------|
| **Complétude des champs clés** | Identifiants site, nom, commune, coords, périodes, CARAC de niveau 1, bibliographie : **excellente** ; **`GEONAME_ID`** entièrement vide dans cet export ; **`COMMENTS`** partiel (~44 %). |
| **Valeurs manquantes hiérarchiques** | `CARAC_LVL2`–`LVL4` volontairement **creux** pour l’immobilier — pas une erreur, mais une contrainte pour l’**enrichissement typologique** fin. |
| **Doublons** | **Aucun doublon** de ligne complète sur les 116 enregistrements. |
| **Cohérence spatiale** | Bornes lat/lon **compatibles** avec le Bade-Württemberg ; répétition de coordonnées identiques = effet **centroïde communal** attendu. |
| **Encodage** | UTF-8 ; caractères allemands et ponctuation bibliographique corrects dans l’échantillon. |
| **Outliers géographiques** | Aucun point hors emprise régionale plausible ; les **« 0 »** en **altitude** méritent un traitement comme **sentinelle** (à normaliser en `NULL` si confirmé). |
| **Précision géolocalisation** | **100 % centroïdes** : qualité **élevée au niveau communal**, **faible pour l’analyse intra-communale** (pas de contour d’enceinte ni de point de fouille). |

En synthèse : qualité **HIGH** pour une **synthèse régionale** et une **carte de synthèse** ; limite **systématique** sur la **précision du point** et sur le **biais thématique** (voir section 7).

---

## 5. Mapping vers le modèle BaseFerRhin

Références : `data/reference/types_sites.json` (alias FR/DE par type canonique), `data/reference/periodes.json` (bornes Hallstatt / La Tène / Transition et motifs textuels), `data/reference/toponymes_fr_de.json` (concordance de noms FR ↔ DE pour affichage et jointures transfrontalières).

Le cœur du domaine est décrit dans `docs/DOMAIN.md` et `src/domain/models/site.py` : agrégat **`Site`**, **`PhaseOccupation`**, **`Source`**.

| Champ ArkeoGIS | Champ BaseFerRhin (ou cible) | Transformation / remarques |
|----------------|------------------------------|----------------------------|
| `SITE_AKG_ID` | `identifiants_externes["arkeogis_site_id"]` | Clé stable externe ; préfixer un `site_id` interne si besoin (ex. `BERNARD-BW-{id}`). |
| `SITE_SOURCE_ID` | `identifiants_externes["bernard_source_id"]` | ID secondaire dans la base source. |
| `SITE_NAME` | `nom_site` | Micro-toponyme allemand conservé ; éventuelles **variantes** via recherche dans `types_sites` / littérature. |
| `MAIN_CITY_NAME` | `commune` | Nom administratif DE ; si affichage bilingue : tenter une résolution via **`toponymes_fr_de.json`** (couverture **surtout Alsace/Bâle** — pour le BW, souvent **pas d’entrée** : garder le nom allemand). |
| — | `pays` | Constante **`DE`**. |
| — | `region_admin` | Ex. **`Baden-Württemberg`** (aligné avec le modèle). |
| `LONGITUDE`, `LATITUDE` | `x_l93`, `y_l93` | Reprojection **EPSG:4326 → EPSG:2154** (pyproj) pour respecter le modèle courant ; conserver lat/lon en attributs dérivés si le pipeline d’export le prévoit. |
| `CITY_CENTROID` = Oui | `precision_localisation` | **`centroïde`** (`PrecisionLocalisation.CENTROIDE`). |
| `ALTITUDE` | `altitude_m` | Parser en float ; traiter **`0`** comme valeur à valider (NULL si sentinelle). |
| `STATE_OF_KNOWLEDGE` | `statut_fouille` | **Fouillé** → `fouille` ; **Sondé** → `prospection` ; **Littérature** → `archivé` ou `signalement` selon politique métier ; **Non renseigné** → `NULL`. |
| `OCCUPATION` | `description` / `commentaire_qualite` | Texte structuré ou phrase résumée ; peu de cardinalité pour un enum domaine. |
| `STARTING_PERIOD`, `ENDING_PERIOD` | `PhaseOccupation.datation_debut`, `datation_fin` | Parser `a:b` → entiers ; si plusieurs lignes par site, **une phase par ligne** ou **fusion** après règles métier. |
| (dérivé des dates) | `PhaseOccupation.periode` | Comparer aux bornes dans **`periodes.json`** : chevauchement majoritaire avec **HALLSTATT** (-800/-450), **LA_TENE** (-450/-25), **TRANSITION** (-500/-400) ; sinon **`indéterminé`** ou phase la plus probable selon overlap. |
| `CARAC_NAME` + `CARAC_LVL1`… | `type_site` (`TypeSite`) | **Enceinte** dominante → **`oppidum`** ou **`habitat`** selon contexte (enceinte majeure / hauteur → privilégier **`oppidum`** via alias *Ringwall*, *Höhensiedlung* dans `types_sites.json`) ; **Dépôt** → **`dépôt`** ; **Habitat** → **`habitat`** ; **Métal** + **Production** / **Forge** → **`atelier`** possible ; reste mobilier seul sur ligne isolée → conserver type site principal sur l’agrégat et mettre le détail en **`mobilier_associe`**. |
| `CARAC_LVL2`–`LVL4` | `PhaseOccupation.mobilier_associe` | Concaténation normalisée (liste de tags FR si politique bilingue). |
| `BIBLIOGRAPHY` | `Source` (type `publication` / `rapport_fouille`) | Une entrée `Source` par référence distincte après **dédoublonnage** inter-lignes du même site. |
| `COMMENTS` | `description` ou `commentaire_qualite` | Fusion contrôlée avec séparateur ; ne pas écraser une description plus riche déjà présente. |
| `DATABASE_NAME` | métadonnée de `Source` / traçabilité ETL | Nom de la base ArkeoGIS et crédit « Bernard ». |

Les enums **`OPPIDUM`, `HABITAT`, `NECROPOLE`, `DEPOT`, `SANCTUAIRE`, `ATELIER`, `VOIE`, `TUMULUS`** du référentiel correspondent aux **`TypeSite`** du code (`oppidum`, `habitat`, etc.) ; utiliser les **alias allemands** (ex. *Hortfund*, *Ringwall*) pour lever l’ambiguïté lors du **NLP** ou du **mapping assisté**.

---

## 6. Stratégie d’ingestion (6 étapes)

1. **Chargement** — Lire le CSV en **`sep=";"`**, **`encoding="utf-8"`**, valider 23 colonnes attendues et le nombre de lignes (116).  
2. **Nettoyage** — Normaliser les booléens texte (`CITY_CENTROID`), parser les plages de dates, convertir altitudes numériques, remplacer altitudes **0** douteuses par **NULL** après règle métier, traiter la **ligne sans bibliographie** (flag qualité).  
3. **Agrégation** — Regrouper par **`SITE_AKG_ID`** pour constituer un **`Site`** unique ; rattacher **plusieurs `PhaseOccupation`** et **sources** ; pour le mobilier détaillé, soit **sous-phases**, soit **liste `mobilier_associe`** sur la phase principale.  
4. **Classification** — Assigner **`TypeSite`** et **`Periode`** via `types_sites.json` et `periodes.json` (overlap temporel + mots-clés éventuels dans `COMMENTS` / biblio).  
5. **Géocodage** — Ici **pas de géocodage adresse** : conserver WGS84, appliquer **reprojection L93** pour le stockage domaine ; optionnel : enrichissement futur par **point précis** (iDAI.gazetteer, données fouille) **sans remplacer** la traçabilité « centroïde d’origine ».  
6. **Export** — Émission **GeoJSON** / **CSV** / **SQLite** conformément aux specs du pipeline (`data/output/...`), avec **`identifiants_externes`** remplis et **`precision_localisation = centroïde`**.

---

## 7. Limites et précautions

- **Biais d’inventaire** : la base est structurée autour des **enceintes** et sites assimilés du Bade-Württemberg ; ce n’est **pas** un inventaire exhaustif de **tous** les types de sites du Fer (nécropoles à la marge, voies rares, etc.).  
- **Géométrie** : **100 % de centroïdes communaux** — les analyses de **distance entre sites voisins** dans une même commune sont **biaisées** ; les densités apparentes peuvent être **sous- ou sur-estimées** selon la taille communale.  
- **Littérature** : références majoritairement **allemandes** (KBW, FBS…) — normal pour la région, mais à intégrer comme **langue source** dans les métadonnées pour la traçabilité.  
- **Couverture géographique** : **BW uniquement** — pas de continuité directe avec l’Alsace dans ce fichier ; la table **`toponymes_fr_de.json`** sert surtout aux **zones frontalières** et à l’**homogénéisation d’affichage**, pas à géocoder le BW.  
- **`GEONAME_ID` vide** : prévoir une **enrichissement optionnel** (API GeoNames ou référentiel administratif BW) si l’on souhaite des jointures administratives fines.  
- **Mobilier sur lignes séparées** : risque de **surestimer** le nombre d’« événements » si l’on compte des lignes au lieu de sites — toujours **agrégation par `SITE_AKG_ID`** pour les statistiques de fréquence des sites.

---

*Document généré à partir de l’export ArkeoGIS et d’une analyse quantitative du fichier CSV (avril 2026).*
