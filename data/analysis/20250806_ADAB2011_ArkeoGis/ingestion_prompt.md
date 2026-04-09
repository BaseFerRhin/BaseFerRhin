# Prompt d’ingestion — ADAB2011 ArkeoGIS (agent exécutable)

Tu es un agent de données chargé d’ingérer, classifier et exporter l’inventaire archéologique **ADAB2011** (ArkeoGIS) dans le cadre du projet **BaseFerRhin** (inventaire de l’âge du Fer du Rhin supérieur).  
Exécute les tâches ci-dessous de bout en bout : charge les fichiers, applique les règles, produis les sorties, valide les contraintes.

---

## Contexte

- **Projet** : BaseFerRhin — harmonisation d’un inventaire protohistorique (âge du Fer) pour analyse spatiale et croisement de sources.
- **Fichier source** : `data/input/20250806_ADAB2011_ArkeoGis.csv`
- **Format** : CSV **ArkeoGIS**, séparateur `;`, **23 colonnes**, encodage **UTF-8**.
- **Volume** : **656 lignes**, **655 sites uniques** (`SITE_AKG_ID`) — inventaire **Nordbaden + Südbaden** (Bade-Wurtemberg).
- **Qualité globale** : **MOYENNE**
  - ~**71,2 %** des périodes début/fin indéterminées (`Indéterminé` ou équivalent).
  - ~**201** valeurs `SITE_NAME` avec guillemets mal formés (souvent `""` en fin de chaîne).
  - ~**81,2 %** des localisations sont des **centroïdes** (précision spatiale faible).
- **Point clé** : le champ **`COMMENTS`** contient des **métadonnées structurées en allemand** (clés du type `# DAT_FEIN : …`, `# TYP_FEIN : …`, `# GENAUIGK_T : …`). Tu **dois** les **parser** et t’en servir pour enrichir types, périodes et précision — ce n’est pas du texte libre ignoré.

Référence descriptive du jeu : `data/analysis/20250806_ADAB2011_ArkeoGis/metadata.json`.

---

## Références obligatoires (à lire avant classification / toponymie)

Tu **dois** t’appuyer sur ces fichiers (chemins relatifs à la racine du dépôt `BaseFerRhin`) :

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Taxonomie des types de sites (codes canoniques, synonymes éventuels). |
| `data/reference/periodes.json` | Périodes et sous-périodes ; champs de matching allemand (ex. `patterns_de` ou équivalent). |
| `data/reference/toponymes_fr_de.json` | Normalisation commune / toponymes FR↔DE si nécessaire pour le matching inter-sources. |
| `data/sources/golden_sites.csv` | Jeu de référence pour contrôle qualité et déduplication. |
| `data/analysis/20250806_ADAB2011_ArkeoGis/metadata.json` | Schéma, stats et contexte du CSV source. |

Pour la **déduplication avec l’analyse LoupBernard** : utilise le répertoire `data/analysis/20250806_LoupBernard_ArkeoGis/` — si un fichier `sites_cleaned.csv` (ou équivalent documenté dans ce dossier) existe, l’utiliser ; sinon, documente dans `quality_report.json` que seuls `metadata.json` / `sample_data.csv` étaient disponibles et base-toi sur `data/output/sites.csv` + `golden_sites.csv` pour les recoupements.

---

## Tâches

### T1 — Chargement et nettoyage

1. **Chargement CSV**
   - Utilise `pandas.read_csv` avec `sep=";"`, `encoding="utf-8"`.
   - Gère les guillemets mal formés : privilégie `quoting=csv.QUOTE_NONE` avec `engine="python"` **ou** une lecture robuste (fallback `on_bad_lines`, `dtype=str` puis conversion) si une ligne casse le parseur — l’objectif est **0 perte de ligne** sur les 656 enregistrements attendus.

2. **`SITE_NAME`**
   - Supprime les motifs de **guillemets parasites en fin de chaîne** (ex. trailing `""`, séquences du type `'""'` signalées dans ~201 lignes).
   - `strip()` sur `SITE_NAME` et `MAIN_CITY_NAME`.

3. **Dates de période (`STARTING_PERIOD` / `ENDING_PERIOD` ou colonnes équivalentes du CSV)**
   - Pour les valeurs datées (~28,8 %), extrais début/fin avec la regex sur le motif **`(-?\d+):(-?\d+)`** (adapter si le séparateur réel diffère légèrement après inspection des données).
   - Pour **`Indéterminé`** (ou chaîne vide / équivalent) → **`None`** / `NaN` pour début et fin (~71,2 %).

4. **Parsing structuré de `COMMENTS`**
   - Extraire au minimum : **`DAT_FEIN`**, **`TYP_FEIN`**, **`TYP_GROB`**, **`GENAUIGK_T`** via regex sur le motif **ligne ou segment** du type `# KEY : value` (espaces autour des `:` tolérés).
   - Stocker ces champs en colonnes dérivées (ex. `comments_dat_fein`, `comments_typ_fein`, …) pour T2–T4.

---

### T2 — Agrégation par site

- Le jeu est **quasi 1:1** : **655 sites** pour **656 lignes** → **une seule duplication** à traiter par **`SITE_AKG_ID`**.
- **Grouper par `SITE_AKG_ID`** : fusionner la ligne dupliquée (priorité : conserver la ligne la plus complète pour `COMMENTS`, coordonnées et champs de période ; documenter la règle dans `quality_report.json`).
- **Enrichissement depuis `COMMENTS` / `DAT_FEIN`** : si les dates ArkeoGIS sont absentes, exploiter les mentions allemandes pouvant orienter la période, par ex. **« Metallzeiten »**, **« Hallstattzeit »**, **« Latènezeit »** — les faire correspondre aux entrées de `periodes.json` (notamment via `patterns_de` ou champs équivalents).
- **Enrichissement type depuis `TYP_FEIN`** (exemples de mapping logique vers codes du projet) :
  - `Grabhügel` → **TUMULUS**
  - `Siedlung` → **HABITAT**
  - `Graben` (contexte enceinte / fortification) → **OPPIDUM**
  - Adapter selon le contenu réel et `types_sites.json`.

---

### T3 — Classification

1. **Type principal** : mapper **`CARAC_LVL1`** (ou colonne équivalente du CSV) vers le code **`type_site`** défini dans `types_sites.json`, avec au minimum les règles suivantes (affiner si le JSON impose d’autres libellés exacts) :
   - `Habitat` → **HABITAT**
   - `Funéraire` → **NECROPOLE**
   - `Enceinte` → **OPPIDUM**
   - `Structure agraire` / `Formation superficielle` / `Charbon` → **INDETERMINE**
   - `Circulation` → **VOIE**

2. **Enrichissement secondaire** depuis **`TYP_FEIN`** (si plus précis que `CARAC_LVL1`) :
   - `Grabhügel` → **TUMULUS**
   - `Siedlung` → **HABITAT**
   - `Meiler` → **ATELIER**
   - Résoudre les conflits avec une règle documentée (ex. priorité au plus spécifique, ou à `TYP_FEIN` si `CARAC_LVL1` est générique).

3. **Période** :
   - Si dates numériques disponibles → déduire `periode` / `sous_periode` via `periodes.json`.
   - Sinon, **fallback** sur mots-clés allemands issus de **`DAT_FEIN`** et matching contre `patterns_de` (ou équivalent) dans `periodes.json`.

4. **`confiance`** (qualitative, cohérente avec le reste du projet) :
   - Par défaut **LOW** : ~81,2 % centroïdes, occupation souvent « Non renseigné », ~71,2 % sans dates fiables.
   - **MEDIUM** si prospection aérienne (ou indicateur équivalent dans les champs source) **et** coordonnées jugées précises (non centroïde ou précision textuelle forte dans `GENAUIGK_T`).
   - Documenter les critères exacts dans `quality_report.json`.

---

### T4 — Géocodage, validation et projection

1. **Filtrage / validation bbox Nordbaden (boîte resserrée)**  
   - **`LONGITUDE` ∈ [7.0, 9.0]`**  
   - **`LATITUDE` ∈ [47.5, 49.0]`**  
   - Toute entité hors boîte : flag explicite dans le rapport (anomalie ou hors périmètre attendu).

2. **Projection** : WGS84 (lon/lat) → **Lambert-93** ; produire **`x_l93`**, **`y_l93`** (EPSG:2154), avec bibliothèque adaptée (`pyproj`, `geopandas`, etc.).

3. **Précision métrique** : parser **`GENAUIGK_T`** pour estimer **`precision_m`** quand c’est possible, ex. :
   - « mit 20 m Toleranz » → ~**20**
   - « mit 50 m Toleranz » → ~**50**
   - « mit Ungenauigkeit bis zu 200m » → ~**200**
   - Si non extractible → `null` + note dans le rapport.

4. **Flag centroïde** : marquer les ~81,2 % des sites dont les coordonnées sont des centroïdes (selon champ source ou heuristique documentée) dans une colonne dédiée du CSV ou dans `quality_report.json` (au minimum une des deux).

---

### T5 — Déduplication inter-sources

Comparer les sites ADAB2011 normalisés avec :

- `data/output/sites.csv` (inventaire consolidé courant du projet),
- `data/sources/golden_sites.csv`,
- et la **sortie de l’analyse LoupBernard** ArkeoGIS (`data/analysis/20250806_LoupBernard_ArkeoGis/`, fichier cleaned si présent).

**Contexte** : ADAB2011 couvre le **Nordbaden**, qui **chevauche** la couverture **BW** de LoupBernard — attend des recoupements notamment vers **Breisach**, **Offenburg** et **Freiburg**.

**Critères de match** (au moins une condition suffisante, à implémenter de façon reproductible) :

- distance **< 500 m** **et** **même commune** (normalisée via `toponymes_fr_de.json` si besoin), **ou**
- similarité de nom (fuzzy) **> 0.85** (ex. `rapidfuzz`, `thefuzz`) avec contrôle géographique raisonnable pour limiter les faux positifs.

Pour chaque paire suspectée : enregistrer dans `quality_report.json` les IDs, scores et décision (fusion proposée / doublon probable / distinct).

---

### T6 — Export

1. **`data/analysis/20250806_ADAB2011_ArkeoGis/sites_cleaned.csv`**  
   Schéma **exact** des colonnes :

   `site_id`, `nom_site`, `commune`, `pays`, `type_site`, `longitude`, `latitude`, `x_l93`, `y_l93`, `periode`, `sous_periode`, `datation_debut`, `datation_fin`, `confiance`, `precision_m`, `source`, `bibliographie`

   - `site_id` : identifiant stable dérivé de `SITE_AKG_ID` (préfixe explicite type `ADAB2011_` + id) — documenter le format dans le rapport.
   - `nom_site` : depuis `SITE_NAME` nettoyé.
   - `commune` : depuis `MAIN_CITY_NAME` (ou champ plus fin si défini dans le CSV).
   - `pays` : **DE** (ou valeur projet standard).
   - `source` : référence lisible (ex. fichier + base ADAB2011 / ArkeoGIS).
   - `bibliographie` : champs bibliographiques du CSV s’ils existent ; sinon vide / `null`.

2. **`data/analysis/20250806_ADAB2011_ArkeoGis/quality_report.json`**  
   Contenu minimal recommandé :
   - comptages (lignes lues, sites uniques, doublons fusionnés),
   - stats bbox, nombre de centroïdes,
   - répartition `confiance`,
   - nombre de lignes **âge du Fer** identifiées (voir Validation),
   - résumé déduplication (nombre de matches vs `sites.csv`, `golden_sites`, LoupBernard),
   - erreurs / avertissements parsing `COMMENTS`.

---

## Validation (obligatoire avant de terminer)

- **655 sites uniques** après agrégation par `SITE_AKG_ID`.
- **Toutes** les coordonnées exportées dans la **bbox Nordbaden** : lon ∈ [7, 9], lat ∈ [47.5, 49.0] — sinon liste des exceptions dans `quality_report.json`.
- **Flag explicite** des **134 lignes** (ou sites, selon le niveau d’agrégation retenu — préciser) correspondant à l’**âge du Fer** : critère à documenter (période datée, mots-clés `DAT_FEIN` / périodes.json, combinaison des deux).
- **Contrôle croisé** avec `golden_sites.csv` et la sortie LoupBernard (si disponible) : synthèse qualitative + métriques dans `quality_report.json`.

---

## Livrables attendus

| Livrable | Chemin |
|----------|--------|
| Sites nettoyés | `data/analysis/20250806_ADAB2011_ArkeoGis/sites_cleaned.csv` |
| Rapport qualité | `data/analysis/20250806_ADAB2011_ArkeoGis/quality_report.json` |
| (Optionnel) Script | `scripts/` ou notebook sous `data/analysis/20250806_ADAB2011_ArkeoGis/` — **uniquement** si le dépôt impose un emplacement ; sinon documenter la commande d’exécution dans le rapport. |

À la fin, résume en français : nombre de sites exportés, taux de centroïdes, nombre de matches inter-sources, et toute anomalie bloquante.
