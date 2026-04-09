# Prompt d’ingestion — Patriarche (EA âge du Fer, export 2025-08-06)

**Usage :** donner ce document tel quel à un agent IA (ou à un développeur) pour exécuter le pipeline d’ingestion depuis la racine du dépôt `BaseFerRhin`. Tous les chemins sont relatifs à cette racine.

**Prérequis Python :** `pandas`, `openpyxl` (ou `python-calamine`) ; optionnel : `rapidfuzz` pour T5.

---

## Contexte

**Projet :** BaseFerRhin — inventaire des sites de l’âge du Fer du Rhin supérieur (Alsace, Bade-Württemberg, Bâle).

**Fichier source :** `data/input/20250806_Patriarche_ageFer.xlsx`  
- Format **Excel** (XLSX), en-tête présente, **5 colonnes**, **836 lignes**.  
- **Identifiant stable :** `Code_national_de_l_EA` (**836** valeurs uniques, 1 ligne par EA).  
- **Sans coordonnées** ; localisation par **`Nom_de_la_commune`** et complément **`Nom_et_ou_adresse`** (souvent vide).  
- **Chronologie et typo** : embarquées dans **`Identification_de_l_EA`** (texte structuré avec `/`).

**Objectif :** charger le fichier, parser l’identification textuelle, normaliser commune et pays, classer période / type selon les référentiels du projet, tenter un géoréférencement par appariement ou géocodage, dédupliquer avec les autres sources, exporter un CSV nettoyé et un rapport qualité JSON.

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Alias FR/DE par type canonique. |
| `data/reference/periodes.json` | Bornes et motifs pour HALLSTATT, LA_TENE, TRANSITION. |
| `data/reference/toponymes_fr_de.json` | Harmonisation des noms de communes FR ↔ DE. |
| `data/sources/golden_sites.csv` | Référence déduplication (séparateur `;`). |
| `data/analysis/20250806_Patriarche_ageFer/metadata.json` | Statistiques et schéma exact des colonnes. |

---

## Tâches

### T1 — Chargement et nettoyage

1. Charger la première feuille (ou la feuille nommée si documentée ailleurs) :
   ```python
   import pandas as pd
   df = pd.read_excel("data/input/20250806_Patriarche_ageFer.xlsx", engine="openpyxl")
   ```
2. Vérifier **836** lignes et colonnes : `Code_national_de_l_EA`, `Identification_de_l_EA`, `Numero_de_l_EA`, `Nom_de_la_commune`, `Nom_et_ou_adresse`.
3. Nettoyage texte : `.astype(str)` puis `.str.strip()` pour colonnes objet ; conserver `Code_national_de_l_EA` en entier ou string stable.
4. Marquer `Nom_et_ou_adresse` comme **vide** si NaN, chaîne vide, ou valeurs sentinelle du type « Localisation inconnue » (à normaliser en `NULL` dans l’export).

### T2 — Parsing de `Identification_de_l_EA`

1. Découper la chaîne sur **`/`** (en gérant espaces multiples) ; documenter le schéma de positions observé sur un échantillon (numéro local, code 67, commune, lieu-dit, **plage chronologique**, **nature**).  
2. Extraire au minimum :
   - une **mention chronologique brute** (ex. « Age du fer », « Age du bronze - Age du fer ») ;  
   - un **indice de structure** ou de fonction (ex. « fosse ») si présent en fin de chaîne.  
3. Conserver la chaîne **complète** dans un champ `identification_ea_brute` pour traçabilité.

### T3 — Classification

**A. Période (`periode`, `sous_periode`, `datation_debut` / `datation_fin` optionnels)**  
- Utiliser `periodes.json` : recherche de **patterns** dans la mention chronologique extraite.  
- Si plusieurs périodes textuelles : appliquer une règle déterministe (ex. **plus récente dominante**, ou **multi-phase** avec liste) et documenter dans `quality_report.json`.

**B. Type de site (`type_site`)**  
- Mapper les mots-clés du segment structurel vers les enums du projet via `types_sites.json` (ex. fosse / structure d’habitat → `HABITAT` ; indices funéraires → `NECROPOLE` ou `TUMULUS` selon contexte).  
- Cas non couverts : `AUTRE` + entrée dans `type_classification_unmapped`.

**C. Confiance**  
- Par défaut **`LOW`** pour la géographie (pas de XY source).  
- **`MEDIUM`** si `Nom_et_ou_adresse` exploitable et géocodage réussi, ou si appariement fort avec une base XY du dépôt.

### T4 — Géoréférencement (pas de projection source)

1. **Pas de coordonnées natives** : ne pas inventer de XY.  
2. Stratégies acceptées (au moins une à tenter, résultats dans le rapport) :
   - appariement sur **`Numero_de_l_EA`** ou texte avec `Alsace_Basel_AF` / `BdD_Proto_Alsace` si clés croisables ;  
   - géocodage adresse (BAN) si `Nom_et_ou_adresse` pertinent ;  
   - fallback **centroïde communal** avec `precision_localisation = centroïde` et `confiance = LOW`.  
3. Si XY obtenues en WGS84, reprojeter en **EPSG:2154** (Lambert-93) pour alignement BaseFerRhin.

### T5 — Déduplication inter-sources

1. Charger `data/output/sites.csv` (adapter séparateur et en-tête réels) et `data/sources/golden_sites.csv`.  
2. Critères possibles sans coordonnées Patriarche :
   - égalité **`Numero_de_l_EA`** / identifiants externes si déjà présents ailleurs ;  
   - fuzzy sur **commune + extrait lieu-dit** depuis `Identification_de_l_EA` (ex. `rapidfuzz`, seuil **≥ 0,85**).  
3. Enregistrer chaque proposition dans `quality_report.json` sous `duplicates_with_golden_or_sites_csv`.

### T6 — Export

1. **CSV nettoyé :** `data/analysis/20250806_Patriarche_ageFer/sites_cleaned.csv`  
   - UTF-8, séparateur `,`.  
   - Colonnes conseillées : `site_id`, `code_national_ea`, `numero_ea`, `identification_ea_brute`, `commune`, `adresse_ou_nom_lieu`, `pays`, `longitude`, `latitude`, `x_l93`, `y_l93`, `periode`, `sous_periode`, `type_site`, `confiance`, `source`, `notes_parsing`.  
   - `site_id` : stable, ex. `PATRIARCHE-{Code_national_de_l_EA}`.  
   - `source` : chaîne fixe documentée, ex. `Patriarche_EA_ageFer_20250806`.

2. **Rapport qualité :** `data/analysis/20250806_Patriarche_ageFer/quality_report.json`  
   - `row_count_raw` (**836**), `unique_code_national` (**836**)  
   - `address_fill_rate`  
   - `parsing_failures` (lignes où segmentation incertaine)  
   - `georef_strategy_counts`  
   - `duplicates_with_golden_or_sites_csv`  
   - `type_classification_unmapped`

---

## Validation (obligatoire)

1. **836** lignes en entrée ; **836** `Code_national_de_l_EA` uniques.  
2. Toutes les lignes ont `Identification_de_l_EA` et `Nom_de_la_commune` non vides après nettoyage.  
3. `periode` alignée sur `periodes.json` ou valeur d’écart documentée.  
4. Fichiers produits non vides : `sites_cleaned.csv`, `quality_report.json`.

---

*Fin du prompt d’ingestion.*
