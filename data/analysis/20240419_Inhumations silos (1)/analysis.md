# Analyse — Inhumations en silos (Alsace-Lorraine)

## 1. Vue d'ensemble

| Élément | Détail |
|--------|--------|
| **Fichier** | `20240419_Inhumations silos (1).xlsx` |
| **Chemin source** | `data/input/20240419_Inhumations silos (1).xlsx` |
| **Format** | XLSX (moteur `openpyxl` / `calamine`) |
| **Volume** | **86 lignes**, **94 colonnes**, ~57 Ko |
| **Export métadonnées** | 2024-04-19 |
| **Contexte archéologique** | Corpus d’**inhumations secondaires dans des silos** (fossés de stockage cerealier réutilisés comme sépultures), caractéristique des dynamiques funéraires du **Bronze final / transition vers l’Hallstatt** et de l’âge du Fer ancien en **Alsace-Lorraine**. Les données intègrent une **anthropologie très détaillée** (âge, sexe, pathologies, position du squelette, parure) et des **datations relatives et radiocarbones**. |

**Projet cible :** BaseFerRhin — inventaire des sites protohistoriques du Rhin supérieur (Alsace, Bade-Wurtemberg, Bâle).

---

## 2. Schéma des colonnes (colonnes clés)

Les statistiques ci-dessous proviennent de `metadata.json`.

### Localisation et site

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Département` | object | ~96,5 % | `68`, `67` |
| `Site` | object | ~94,2 % | Bergheim, Berstett, Bischoffsheim |
| `Lieu dit` | object | ~94,2 % | Saulager, Langenberg, Bischenberg |
| `X(L93)` | float64 | ~79,1 % | 1024887, 1044392 |
| `Y(L93)` | float64 | ~79,1 % | 6797044, 6850994 |

### Fouille et structure

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Année fouille` | object | ~93 % | 2012, 2018, 1973 |
| `N° structure` | object | ~90,7 % | 351, 643, 2026 |
| `N° individu` | object | ~91,9 % | 1, 2, x |
| `Type de silo` | object | ~91,9 % | Cylindrique, Tronconique, Fond de fosse |

### Datation

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Datation relative` | object | ~91,9 % | Ha D3-LT A1, LT C1, Ha D, Ha D1-D2 |
| `Datation absolue` | object | ~53,5 % | indicateurs de présence |
| `num datation (code labo)` | object | ~57 % | Poz-118235, Poz-133830 |
| `âge radiocarbone` | object | ~55,8 % | 2225 ± 30 BP |
| `14C (2 sigma)` | object | ~60,5 % | 380-203, 780-540 avant J.C |
| `biblio` | object | ~69,8 % | références bibliographiques |

### Anthropologie et dépôt (aperçu)

Nombreuses colonnes de type **case à cocher / libellé** (orientation, position tête, sexe, tranches d’âge, pathologies, position du corps, parure : bracelet, fibule, etc.). Taux de remplissage souvent **< 50 %** par colonne (grille analytique large). Colonne `Précision âge` ~67,4 % rempli.

### Anomalies de schéma

- `Unnamed: 93` : colonne résiduelle (~14 % rempli) — notes complémentaires sur datations, rapports.
- Nom de colonne avec saut de ligne : `Précision \nâge` (à normaliser en code).

---

## 3. Modèle de données (grain)

- **Une ligne = une inhumation individuelle** dans une structure de type silo (ou assimilée), au sein d’un site nommé (`Site` + `Lieu dit` + département).
- Ce n’est **pas** une ligne par site : plusieurs individus peuvent partager les mêmes coordonnées / le même site.
- Pour l’intégration **site-level** BaseFerRhin, il faut **agrégation** (par ex. groupement par `Site` + `Lieu dit` + `Département` ± coordonnées L93).

---

## 4. Qualité

| Aspect | Constat |
|--------|---------|
| **Valeurs manquantes** | Coordonnées **X/Y L93 ~20,9 %** vides ; champs anthropologiques très parcimonieux ; **taux de remplissage moyen ~33,8 %** sur l’ensemble des colonnes. |
| **Système de coordonnées** | Lambert-93 (EPSG:2154) — plages cohérentes pour l’Est de la France (X ~1,02–1,05 Mm, Y ~6,74–6,87 Mm). |
| **Chronologie** | `Datation relative` bien renseignée ; présence Hallstatt / La Tène / transitions dans les échantillons. |
| **Métadonnées qualité** | `confidence_level`: **LOW** ; issue signalée : **1 colonne sans nom** (`Unnamed: 93`). |
| **Lignes parasites** | Présence possible de lignes de **total** (`TOTAL` dans `Département` / `Site` selon échantillons) — à filtrer à l’ingestion. |

---

## 5. Mapping vers BaseFerRhin

| Cible BaseFerRhin | Source proposée | Remarques |
|-------------------|-----------------|-----------|
| `nom_site` | `Site` + complément `Lieu dit` si pertinent | Éviter les libellés génériques ; harmoniser avec `toponymes_fr_de.json`. |
| `commune` | `Site` (souvent commune) ou champ dérivé | Vérifier cohérence avec `Département` (67/68/57/54…). |
| `pays` | `Département` → `FR` (Alsace/Moselle/Lorraine) | Adapter si extension ultérieure. |
| `type_site` | **NECROPOLE** et/ou **HABITAT** | Sépulture en silo = pratique funéraire sur **habitat** ouvert ; alias `silo`, `sépulture`, `inhumation` dans `types_sites.json`. Discriminer selon règle métier (priorité nécropole vs habitat). |
| `x_l93`, `y_l93` | `X(L93)`, `Y(L93)` | Laisser vides si manquant ; contrôler plages France métro. |
| `periode` / `sous_periode` | Parser `Datation relative` (+ éventuellement `14C`) | Aligner sur `periodes.json` : **HALLSTATT** (-800/-450), **LA_TENE** (-450/-25), **TRANSITION** (Ha D3/LT A). |
| `datation_debut` / `datation_fin` | Intervalles `14C (2 sigma)` ou bornes issues sous-périodes | Optionnel, parsing manuel / règles. |
| Champs richesse funéraire | Parure, mobilier, `biblio` | Peuvent alimenter des tables d’extension ou `source_references`, pas le schéma minimal sites. |

---

## 6. Stratégie d’ingestion

1. **Chargement** : `pandas.read_excel(..., engine="openpyxl")` ; normaliser les noms de colonnes (espaces, `\n`).
2. **Nettoyage** : exclure lignes `TOTAL` / agrégats ; convertir X/Y en numérique ; flaguer coordonnées hors emprise plausible L93.
3. **Classification** : mapper `type_site` via alias FR/DE de `types_sites.json` ; parser `Datation relative` vers clés `HALLSTATT` / `LA_TENE` / `TRANSITION` et sous-périodes Ha C, D1, D2, D3, LT A…
4. **Projection** : le référentiel interne peut conserver **L93** (comme `sites.csv`) ; si besoin carto web, **pyproj** `EPSG:2154` → `EPSG:4326` (WGS84).
5. **Agrégation site** : `groupby` sur clé site + coords ; conserver en parallèle une table **sépultures** (grain ligne) si le modèle évolue.
6. **Export** : lignes normalisées compatibles schéma cible (voir `data/output/sites.csv`) + traçabilité fichier source.

---

## 7. Limites

- **Précision spatiale** : ~21 % des inhumations **sans coordonnées** ; les points sont souvent **centroïdes de site**, pas la fosse exacte.
- **Couverture chronologique** : centrée **Hallstatt / début La Tène** ; Bronze final selon contexte — **hors bornes strictes** du JSON `periodes` pour le seul Bz (prévoir période étendue ou champ « indéterminé »).
- **Complétude** : anthropologie riche mais **très creuse** colonne par colonne ; risque d’**sur-interprétation** des absences.
- **Granularité** : données **individuelles** ; fusion avec inventaire **par site** non triviale.

---

*Document généré à partir de `metadata.json` du dossier d’analyse et des référentiels `data/reference/`.*
