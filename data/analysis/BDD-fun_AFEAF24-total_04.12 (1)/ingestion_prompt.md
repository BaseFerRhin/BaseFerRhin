# Prompt d’ingestion — AFEAF 2024 base funéraire (total 04.12)

**Usage :** donner ce document tel quel à un agent IA (ou à un développeur) pour exécuter le pipeline d’ingestion depuis la racine du dépôt `BaseFerRhin`. Tous les chemins sont relatifs à cette racine.

**Prérequis Python :** `pandas`, `openpyxl` ; optionnel : `rapidfuzz`, `pyproj` si géocodage / projection.

---

## Contexte

**Projet :** BaseFerRhin — inventaire des sites de l’âge du Fer du Rhin supérieur.

**Fichier source :** `data/input/BDD-fun_AFEAF24-total_04.12 (1).xlsx`  
- **401** lignes, **63** colonnes.  
- **Structure complexe** : en-têtes **multi-niveaux** ; **48 colonnes `Unnamed:`** — les intitulés fonctionnels sont souvent sur la **première ligne de données** ou combinés avec la ligne d’en-tête Excel.  
- **Contenu** : pratiques funéraires (NMI, types de dépôt, monuments, fosses, mobilier, réinterventions, positions, âge/sexe, datations Hallstatt/La Tène, C14).  
- **Pas de coordonnées** explicites ; site décrit par **`info SITE`** (département) et **`Unnamed: 1`** (libellé site).  
- **Grain** : à définir (site, structure `N° ST`, ou individu) — le fichier peut exiger **plusieurs lignes** par site.

**Objectif :** reconstruire un schéma tabulaire propre, normaliser les valeurs catégorielles, agréger selon le grain retenu, mapper vers types et périodes BaseFerRhin, géoréférencer par jointure, exporter CSV + rapport qualité.

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | NECROPOLE, TUMULUS, DEPOT, etc. |
| `data/reference/periodes.json` | Hallstatt / La Tène / sous-périodes. |
| `data/reference/toponymes_fr_de.json` | Normalisation des noms de lieux. |
| `data/sources/golden_sites.csv` | Déduplication. |
| `data/analysis/BDD-fun_AFEAF24-total_04.12 (1)/metadata.json` | Liste des 63 colonnes et statistiques. |

---

## Tâches

### T1 — Chargement et reconstruction du schéma

1. Charger le classeur **sans** supposer que la ligne 0 = seul en-tête :
   ```python
   import pandas as pd
   raw = pd.read_excel("data/input/BDD-fun_AFEAF24-total_04.12 (1).xlsx", engine="openpyxl", header=None)
   ```
2. Inspecter les **3–5 premières lignes** : identifier les cellules **DPT**, **SITE**, **N° ST**, **NMI**, etc.  
3. Construire une **liste de noms de colonnes canoniques** en concaténant (ex.) « groupe » + « sous-libellé » pour chaque index de colonne.  
4. Re-lire ou tronquer les lignes d’**étiquettes** pures pour obtenir un DataFrame où **chaque ligne = un enregistrement funéraire** (401 lignes data attendues après retrait des éventuelles lignes de légende — **valider** contre le nombre de sites structures réels).  
5. Renommer toutes les colonnes `Unnamed:*` en noms stables (snake_case).

### T2 — Nettoyage des valeurs

1. Normaliser **`oui` / `non` / `probable` / `indéterminé`** en enum ou booléen nullable.  
2. Traiter **`*`** comme **NULL** / « non applicable » sauf convention contraire documentée.  
3. `str.strip()` sur tous les champs texte ; gérer retours à la ligne dans les en-têtes originels.  
4. Colonne **`DATATION `** (attention à l’espace final du nom source) : préserver le texte brut + champs dérivés parsés.

### T3 — Classification (période et type)

**A. Période**  
- Matcher `DATATION `, `phase chrono relative`, et champs C14 contre `periodes.json` (patterns FR + intervalles BC/BP si parsables).  
- Remplir `periode` = `HALLSTATT` | `LA_TENE` | `TRANSITION` | vide, et `sous_periode` si correspondance claire (Ha D1, LT A…).

**B. Type de site**  
- Par défaut **`NECROPOLE`** ou **`TUMULUS`** selon colonnes tumulus / enclos / fosse sépulcrale et `types_sites.json`.  
- Si absence totale d’indice monument : **`NECROPOLE`** avec `commentaire_qualite` expliquant l’hypothèse.

**C. Confiance**  
- **`MEDIUM`** si datation textuelle claire ; **`LOW`** si surtout `indéterminé`.

### T4 — Géoréférencement

1. Parser **`Unnamed: 1`** pour extraire **commune** (heuristique : texte avant première virgule, ou dictionnaire de communes 67/68) — **valider** sur échantillon.  
2. Jointure avec **`Alsace_Basel_AF`** ou géocodage BAN ; utiliser `toponymes_fr_de.json` pour variantes.  
3. Reprojection **EPSG:2154** si lon/lat obtenues.

### T5 — Agrégation et déduplication

1. Définir **`site_key`** stable : ex. `hash(normalize(DPT) + "|" + normalize(libelle_site))`.  
2. Agréger **NMI** au niveau site : documenter si **somme**, **max**, ou **dernière ligne** (éviter double comptage).  
3. Dédupliquer avec `golden_sites.csv` / `sites.csv` (fuzzy + distance si coords).

### T6 — Export

1. **CSV structure (recommandé) :** `data/analysis/BDD-fun_AFEAF24-total_04.12 (1)/sepultures_long.csv`  
   - Une ligne par **ligne source** après nettoyage, avec colonnes renommées + `site_key` + `numero_structure` (`Unnamed: 2`).  

2. **CSV site (agrégé) :** `data/analysis/BDD-fun_AFEAF24-total_04.12 (1)/sites_cleaned.csv`  
   - Une ligne par **`site_key`** avec : `site_id`, `departement`, `nom_site_brut`, `commune_inferée`, `nmi_total_ou_max`, `periode`, `sous_periode`, `type_site`, `longitude`, `latitude`, `x_l93`, `y_l93`, `confiance`, `source`, `resume_pratiques` (texte concaténé court).  

3. **Rapport :** `data/analysis/BDD-fun_AFEAF24-total_04.12 (1)/quality_report.json`  
   - `row_count_raw`, `data_rows_after_header_fix`  
   - `columns_renamed_from_unnamed` (mapping)  
   - `period_unmapped`  
   - `commune_parse_failures`  
   - `duplicates_with_golden_or_sites_csv`  
   - `aggregation_rule_nmi` (documentation explicite)

4. `source` : chaîne fixe, ex. `AFEAF_funeraire_2024_total_0412`.

---

## Validation (obligatoire)

1. Le mapping **colonne par colonne** des **`Unnamed`** est **documenté** dans le rapport (au moins pour les blocs NMI, monument, fosse, datation).  
2. Aucune datation inventée : uniquement parsing des champs source.  
3. Règle **`site_key` + NMI** explicitement écrite dans `quality_report.json`.  
4. Fichiers produits non vides : au minimum `sites_cleaned.csv` (ou équivalent agrégé) et `quality_report.json`.

---

*Fin du prompt d’ingestion.*
