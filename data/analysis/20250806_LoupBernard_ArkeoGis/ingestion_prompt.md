# Prompt d’ingestion — ArkeoGIS Loup/Bernard (Bade-Wurtemberg)

**Usage :** donner ce document tel quel à un agent IA (ou à un développeur) pour exécuter le pipeline d’ingestion depuis la racine du dépôt `BaseFerRhin`. Tous les chemins sont relatifs à cette racine.

**Prérequis Python :** `pandas`, `pyproj`, `rapidfuzz` (optionnel mais requis pour T5 : `pip install pandas pyproj rapidfuzz`).

---

## Contexte

**Projet :** BaseFerRhin — inventaire des sites de l’âge du Fer du Rhin supérieur (données normalisées, référentiels partagés, fusion multi-sources).

**Fichier source :** `data/input/20250806_LoupBernard_ArkeoGis.csv`  
- Format **CSV ArkeoGIS** : séparateur `;`, encodage **UTF-8**, en-tête présente, **23 colonnes**.  
- **Volume :** 116 lignes, **105 sites uniques** (`SITE_AKG_ID`). Fortifications et sites du Fer en Bade-Württemberg (Allemagne).  
- **Qualité :** élevée — datations renseignées, bibliographie ~99 %, pas de problèmes d’encodage majeurs.  
- **Particularité :** coordonnées **100 % centroïdes communaux** (`CITY_CENTROID=Oui`) ; typologie dominante **« Enceinte »** ; bibliographie riche en allemand.

**Objectif de ce prompt :** charger ce CSV, agréger par site, classifier types et périodes selon les référentiels du projet, projeter en Lambert-93, détecter les doublons avec les autres sources, puis exporter un CSV nettoyé et un rapport de qualité JSON.

---

## Références obligatoires

L’agent **doit** lire et s’appuyer sur les fichiers suivants (ne pas improviser les listes de types ou d’intervalles chronologiques) :

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Alias FR/DE par `type_site` canonique (`OPPIDUM`, `HABITAT`, `DEPOT`, etc.). |
| `data/reference/periodes.json` | Bornes `date_debut` / `date_fin` pour `HALLSTATT`, `LA_TENE`, `TRANSITION` et sous-périodes. |
| `data/reference/toponymes_fr_de.json` | Harmonisation des noms de communes FR/DE si nécessaire pour le rapprochement inter-sources. |
| `data/sources/golden_sites.csv` | Sites de référence pour la déduplication et le contrôle croisé (séparateur `;`, en-tête : `commune`, `type_mention`, etc.). |
| `data/analysis/20250806_LoupBernard_ArkeoGis/metadata.json` | Métadonnées décrivant colonnes, grain (1 site = N lignes CARAC), comptages et bornes géographiques observées. |

---

## Tâches

### T1 — Chargement et nettoyage

1. Charger le fichier :
   ```python
   import pandas as pd
   df = pd.read_csv("data/input/20250806_LoupBernard_ArkeoGis.csv", sep=";", encoding="utf-8")
   ```
2. **Nettoyage minimal** (qualité déjà élevée) :
   - Pour `SITE_NAME` et `MAIN_CITY_NAME` : appliquer `.str.strip()` après conversion en string (gérer les NaN si jamais présents).
3. **Parser les périodes** `STARTING_PERIOD` et `ENDING_PERIOD` (format ArkeoGIS `"début:fin"` avec années négatives pour av. J.-C.) :
   - Expression régulière : `r"(-?\d+):(-?\d+)"` → tuple `(int, int)` pour chaque colonne.
   - Conserver les entiers tels quels (années astronomiques, négatives = av. J.-C.).
4. Il n’y a **pas** de valeurs « indéterminées » à traiter spécifiquement dans ce lot (cf. `metadata.json`).

### T2 — Agrégation par site

1. **Grouper par** `SITE_AKG_ID` (attendu : **105 groupes** ; la plupart ont 1 ligne ; le site **Neuenbürg** `#25833` en a **12**).
2. Pour chaque groupe :
   - **CARAC_*** : construire une **liste de dictionnaires** (une entrée par ligne source), clés au minimum : `CARAC_NAME`, `CARAC_LVL1`, `CARAC_LVL2`, `CARAC_LVL3`, `CARAC_LVL4`, `CARAC_EXP` (ignorer ou mettre `null` les niveaux vides).
   - **BIBLIOGRAPHY** : concaténer toutes les chaînes non vides, **dédupliquer** (après strip), ordre stable (ex. ordre d’apparition) ; séparateur recommandé entre entrées : ` | ` ou ` ; `, documenté dans le rapport.
   - **COMMENTS** : fusionner les commentaires non vides (ex. joindre avec ` ; `), en évitant les doublons exacts après strip.
   - **Coordonnées, commune, nom de site, état des lieux** : une seule valeur par site (identique sur toutes les lignes d’un même `SITE_AKG_ID` pour lon/lat et périodes — vérifier en agrégation ; en cas d’écart, consigner dans `quality_report.json`).
3. Conserver un identifiant stable pour la traçabilité : `SITE_AKG_ID` (et éventuellement `SITE_SOURCE_ID` dans le rapport, pas obligatoire dans le CSV final).

### T3 — Classification

**A. Type de site (`type_site`) à partir de `CARAC_LVL1`**

- Correspondance directe :
  - `"Enceinte"` → `OPPIDUM`
  - `"Habitat"` → `HABITAT`
  - `"Dépôt"` → `DEPOT`
- Si **plusieurs** `CARAC_LVL1` distincts pour un même site après agrégation, appliquer la **priorité** :  
  **Enceinte > Habitat > Dépôt > autres**.
- Pour toute valeur `CARAC_LVL1` non couverte par les trois libellés ci-dessus : choisir le type le plus cohérent avec `types_sites.json` (aliases) si possible ; sinon utiliser une valeur explicite du référentiel (ex. `ATELIER`, `SANCTUAIRE`…) ou à défaut `AUTRE` **et** lister ces cas dans `quality_report.json` sous `type_classification_unmapped`.

**B. Période (`periode`, `sous_periode`) à partir des entiers `datation_debut` / `datation_fin`**

- Utiliser **uniquement** les intervalles de `data/reference/periodes.json` pour les clés : `HALLSTATT`, `LA_TENE`, `TRANSITION`.
- Logique recommandée (à appliquer de façon déterministe) :
  - Calculer l’**intersection** (en années) entre `[datation_debut, datation_fin]` du site et chaque grande période.
  - Affecter `periode` selon la **plus forte couverture** (longueur d’intersection). En cas d’égalité, prioriser : `TRANSITION` si chevauchement fort avec les deux bornes Hallstatt/La Tène, sinon ordre documenté dans le rapport.
  - `sous_periode` : optionnel ; si une sous-période du JSON recoupe majoritairement l’intervalle du site, la renseigner ; sinon laisser vide.
- Recopier `datation_debut` / `datation_fin` dans le CSV export (entiers, années négatives = av. J.-C.).

**C. Confiance géographique / source**

- **Par défaut :** `confiance` = `LOW` pour tous les sites (**100 % centroïdes communaux**).
- **Exception :** si `STATE_OF_KNOWLEDGE == "Fouillé"` → `confiance` = `MEDIUM`.
- Le champ `source` dans l’export doit identifier clairement la provenance (ex. chaîne fixe `ArkeoGIS_LoupBernard_BW_20250806` ou équivalent stable).

### T4 — Géocodage et projection

1. **Validation des coordonnées WGS84** (points en degrés décimaux) :
   - `LONGITUDE` ∈ **[7.0, 11.0]**
   - `LATITUDE` ∈ **[47.0, 50.0]**
   - Toute valeur hors bornes : ligne/site à signaler dans `quality_report.json` (`coordinates_out_of_bounds`), sans silencieusement corriger.
2. **Projection vers Lambert-93 (EPSG:2154)** :
   ```python
   from pyproj import Transformer
   transformer = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
   x_l93, y_l93 = transformer.transform(longitude, latitude)
   ```
3. **Marquage sémantique :** considérer **toutes** les coordonnées comme **centroïdes de commune** (`CITY_CENTROID=Oui` sur la source) ; le rapport doit le rappeler (`coordinate_role: "city_centroid"` pour 100 % des sites).

### T5 — Déduplication inter-sources

1. Charger :
   - `data/output/sites.csv` (export courant du projet — séparateur `,`, colonnes telles que `nom_site`, `commune`, `longitude`/`latitude` ou `x_l93`/`y_l93` selon le fichier : **adapter** en relisant l’en-tête réel).
   - `data/sources/golden_sites.csv` (séparateur `;`).
2. **Critères de rapprochement** (un match si **au moins une** condition est vraie) :
   - **Géo + commune :** distance haversine (ou équivalent) **< 500 m** **et** même commune normalisée (après strip, comparaison insensible à la casse ; utiliser `toponymes_fr_de.json` pour aligner variantes FR/DE quand c’est pertinent).
   - **OU** correspondance floue sur le nom : `rapidfuzz.fuzz.token_sort_ratio` (ou `ratio` normalisé sur noms de site + commune) **> 0.85** entre le site ingéré et une entrée existante.
3. Pour chaque paire détectée, enregistrer dans `quality_report.json` : `potential_duplicate_of`, critère utilisé, identifiant ou nom de l’enregistrement cible.
4. **Chevauchements connus à anticiper :** **Breisach am Rhein**, **Heuneburg** peuvent figurer à la fois dans ce lot et dans `golden_sites.csv` — les traiter comme doublons potentiels à documenter, **sans fusion automatique obligatoire** sauf consigne projet ; l’agent doit au minimum **signaler** et **ne pas dupliquer aveuglément** dans un merge final si le dépôt impose une clé unique (sinon, exporter tel quel et laisser la décision de fusion humaine).

### T6 — Export

1. **CSV nettoyé :** `data/analysis/20250806_LoupBernard_ArkeoGis/sites_cleaned.csv`  
   - Encodage UTF-8, séparateur `,`.  
   - **Schéma exact des colonnes (ordre conseillé) :**  
     `site_id`, `nom_site`, `commune`, `pays`, `type_site`, `longitude`, `latitude`, `x_l93`, `y_l93`, `periode`, `sous_periode`, `datation_debut`, `datation_fin`, `confiance`, `source`, `bibliographie`  
   - `site_id` : identifiant unique dérivé de manière stable (ex. préfixe `AKG-` + `SITE_AKG_ID`, ou hash déterministe documenté).  
   - `pays` : `"DE"` pour ce jeu Bade-Württemberg.  
   - `commune` : privilégier `MAIN_CITY_NAME` stripé ; `nom_site` : `SITE_NAME` stripé.  
   - `bibliographie` : texte agrégé dédupliqué (T2).

2. **Rapport de qualité :** `data/analysis/20250806_LoupBernard_ArkeoGis/quality_report.json`  
   Contenu minimal recommandé :
   - `input_file`, `export_date_iso`, `row_count_raw`, `site_count_aggregated` (attendu **105**)
   - `coordinates_out_of_bounds` (liste)
   - `period_inconsistencies` (lignes où STARTING/ENDING varieraient intra-site — attendu vide)
   - `type_classification_unmapped` (liste)
   - `duplicates_with_golden_or_sites_csv` (liste d’objets)
   - `bibliography_null_count` (après agrégation)
   - `notes` : rappel **100 % centroïdes**, référence à `metadata.json`

---

## Validation (obligatoire avant de considérer le travail terminé)

1. **Comptage :** exactement **105** sites uniques après agrégation par `SITE_AKG_ID`.
2. **Géographie :** toutes les paires (lon, lat) valides sont dans la boîte **[7, 11] × [47, 50]** ; sinon expliciter les exceptions dans le rapport.
3. **Chronologie :** vérifier que pour chaque site, les dates parsées sont cohérentes (`datation_debut <= datation_fin`) et que `periode` est l’une de `HALLSTATT`, `LA_TENE`, `TRANSITION` (ou documenter toute dérogation).
4. **Contrôle croisé :** exécuter les comparaisons décrites en T5 avec `golden_sites.csv` (et `sites.csv`) et consigner les résultats dans `quality_report.json`.
5. **Fichiers produits présents et non vides :** `sites_cleaned.csv` et `quality_report.json` sous `data/analysis/20250806_LoupBernard_ArkeoGis/`.

---

*Fin du prompt d’ingestion.*
