# Prompt d’ingestion — BdD Proto Alsace

**Usage :** donner ce document tel quel à un agent IA (ou à un développeur) pour exécuter le pipeline d’ingestion depuis la racine du dépôt `BaseFerRhin`. Tous les chemins sont relatifs à cette racine.

**Prérequis Python :** `pandas`, `openpyxl` ; optionnel : `rapidfuzz` pour appariements.

---

## Contexte

**Projet :** BaseFerRhin — inventaire des sites de l’âge du Fer du Rhin supérieur.

**Fichier source :** `data/input/BdD_Proto_Alsace (1).xlsx`  
- **1127** lignes, **23** colonnes.  
- **Sans coordonnées**.  
- **Clé unique :** `id` (**1127** uniques).  
- **Typologie :** `type_site` (7 valeurs, **≈ 0,3 %** de null).  
- **Chronologie :** `datation_1` (toujours rempli), `datation_2` partiel ; colonnes **`BA`**, **`BM`**, **`BF1`**, **`BF2`**, **`BF3_HaC`**, **`HaD`**, **`LTAB`**, **`LTCD`** = indicateurs 0/1 avec beaucoup de null.  
- **Colonnes entièrement vides :** `type_precision`, `conservati` (à ignorer).  
- **Confiance métadonnées :** LOW ; remplissage moyen **≈ 41,5 %**.

**Objectif :** charger, filtrer (optionnel) sur la composante **âge du Fer**, mapper types et périodes via les référentiels, enrichir avec coordonnées par jointure, exporter CSV + rapport qualité.

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Types canoniques et alias. |
| `data/reference/periodes.json` | HALLSTATT, LA_TENE, TRANSITION et sous-périodes. |
| `data/reference/toponymes_fr_de.json` | Noms de communes. |
| `data/sources/golden_sites.csv` | Déduplication. |
| `data/analysis/BdD_Proto_Alsace (1)/metadata.json` | Schéma et statistiques. |

---

## Tâches

### T1 — Chargement et nettoyage

1.  
   ```python
   import pandas as pd
   df = pd.read_excel("data/input/BdD_Proto_Alsace (1).xlsx", engine="openpyxl")
   ```
2. Vérifier **1127** lignes, **23** colonnes ; supprimer du pipeline les colonnes **`type_precision`** et **`conservati`** si elles sont 100 % NaN.  
3. `str.strip()` sur `commune`, `lieu_dit`, `datation_1`, `datation_2`, `biblio`, `structures`, `rq`.  
4. Normaliser flags `BA`…`LTCD` : NaN → 0 ou « absent » selon convention documentée ; valeur **1.0** → présent.

### T2 — Filtrage « pertinent Fer » (recommandé)

1. Inclure une ligne si **au moins une** condition est vraie :
   - `LTAB == 1` ou `LTCD == 1` ou `HaD == 1` ou `BF3_HaC == 1` ;  
   - **ou** `datation_1` / `datation_2` matchent des motifs de `periodes.json` (Hallstatt, La Tène, « Hallstatt », « La Tène », codes Ha D, LT…).  
2. Exclure explicitement les entrées **uniquement** Bronze ancien/moyen **sans** aucun indice Fer, si la politique projet = inventaire Fer strict.  
3. Conserver un fichier intermédiaire ou une colonne `included_fer_policy` pour audit.

### T3 — Classification

**A. `type_site` (enum projet)**  
- `funéraire` → `NECROPOLE` par défaut ; si `structures` mentionne tumulus / tertre → envisager `TUMULUS`.  
- `habitat` → `HABITAT` ; indices enceinte / hauteur → `OPPIDUM` si règle métier.  
- `mobilier` → `DEPOT` si dépôt / trouvaille isolée cohérente avec `type_oa` ; sinon `HABITAT` ou `AUTRE` documenté.  
- Autres valeurs du fichier : mapper via `types_sites.json` ou `AUTRE` + `type_classification_unmapped`.

**B. Période**  
- Parser `datation_2` en priorité pour `sous_periode` (ex. Ha D1 → aligner sur clés `sous_periodes` de `periodes.json`).  
- Déduire `periode` (HALLSTATT / LA_TENE / TRANSITION) par **chevauchement d’intervalles** ou par **patterns** textuels.  
- Si ambigu : `periode` la plus conservative + note dans le rapport.

**C. `statut_fouille`** (indicatif)  
- `type_oa` = fouille → `fouille` ; diagnostic → `prospection` ; découverte isolée → `signalement` ou équivalent projet.

### T4 — Géoréférencement par jointure

1. **Pas de XY natives** : tenter :
   - jointure sur (`commune`, normalisation `lieu_dit`) avec **`Alsace_Basel_AF`** ;  
   - jointure sur **`EA`** normalisé avec **`Numero_de_l_EA`** Patriarche si formats compatibles.  
2. Si succès : reprojeter en **EPSG:2154** ; `confiance` selon qualité du match.  
3. Sinon : laisser coords vides, `confiance = LOW`.

### T5 — Déduplication inter-sources

1. Comparer aux sites déjà dans `data/output/sites.csv` et `golden_sites.csv` (fuzzy commune + lieu-dit + biblio partagée).  
2. Consigner `potential_duplicate_of` dans `quality_report.json`.

### T6 — Export

1. **CSV :** `data/analysis/BdD_Proto_Alsace (1)/sites_cleaned.csv`  
   - Colonnes conseillées : `site_id`, `id_proto`, `commune`, `lieu_dit`, `type_site`, `type_site_canon`, `periode`, `sous_periode`, `datation_1_brut`, `datation_2_brut`, `longitude`, `latitude`, `x_l93`, `y_l93`, `statut_fouille`, `confiance`, `source`, `bibliographie`, `structures_resume`, `remarques`, `ea`, `oa`.  
   - `site_id` : ex. `PROTO-ALS-{id}`.  
   - `source` : `BdD_Proto_Alsace_xlsx`.

2. **Rapport :** `data/analysis/BdD_Proto_Alsace (1)/quality_report.json`  
   - `row_count_raw`, `row_count_after_fer_filter`  
   - `type_classification_unmapped`  
   - `period_parse_failures`  
   - `join_spatial_success_count`  
   - `duplicates_with_golden_or_sites_csv`  
   - `dropped_columns` : `type_precision`, `conservati`

---

## Validation (obligatoire)

1. **1127** lignes en entrée ; **1127** `id` uniques lus.  
2. Politique de filtrage Fer **documentée** (même si « tout importer »).  
3. Aucune invention de coordonnées sans jointure ou géocodage.  
4. Fichiers produits : `sites_cleaned.csv`, `quality_report.json`.

---

*Fin du prompt d’ingestion.*
