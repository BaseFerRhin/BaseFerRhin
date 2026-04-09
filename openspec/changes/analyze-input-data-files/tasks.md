## 1. Setup — Structure des dossiers et script

- [x] 1.1 Créer le dossier `data/analysis/` et les sous-dossiers `20250806_LoupBernard_ArkeoGis/` et `20250806_ADAB2011_ArkeoGis/`
- [x] 1.2 Créer le script `scripts/analyze_input_files.py` avec la structure de base (argparse, itération sur `data/input/*.csv`, imports pandas/json/pathlib)

## 2. Metadata JSON — Génération par fichier

- [x] 2.1 Implémenter le chargement CSV (`pd.read_csv`, sep=`;`, encoding=`utf-8`) avec gestion des guillemets malformés
- [x] 2.2 Implémenter le profiling des colonnes (name, dtype, null_count, null_pct, unique_count, sample_values)
- [x] 2.3 Implémenter l'extraction de la provenance source (platform, database_name, export_date depuis le nom de fichier)
- [x] 2.4 Implémenter le calcul de l'emprise géographique (bounding box, city_centroid_pct)
- [x] 2.5 Implémenter le profil chronologique (parsing `-YYYY:-YYYY`, earliest/latest, indeterminate_rows/pct)
- [x] 2.6 Implémenter l'évaluation qualité (completeness metrics, issues detection, confidence_level)
- [x] 2.7 Implémenter la documentation du grain de données (rows_per_site_avg/max, unique_sites_count via SITE_AKG_ID)
- [x] 2.8 Écrire le `metadata.json` final et le `sample_data.csv` (20 premières lignes)

## 3. Analysis Markdown — Documentation par fichier

- [x] 3.1 Générer la section "Vue d'ensemble" (nom, origine, taille, contexte archéologique)
- [x] 3.2 Générer la section "Schéma détaillé des colonnes" avec stats et top values par colonne
- [x] 3.3 Générer la section "Analyse du modèle de données" (grain multi-lignes, hiérarchie CARAC_*, ratio lignes/sites)
- [x] 3.4 Générer la section "Analyse de qualité" (manquants, aberrants, doublons, encodage, centroïdes)
- [x] 3.5 Générer la section "Mapping vers le modèle BaseFerRhin" (table de correspondance référençant types_sites.json, periodes.json, toponymes_fr_de.json)
- [x] 3.6 Générer la section "Stratégie d'ingestion" (6 étapes : chargement, nettoyage, agrégation, classification, géocodage, export)
- [x] 3.7 Générer la section "Limites et précautions" (biais inventaire, précision spatiale, datation, bilingue FR/DE)
- [x] 3.8 Écrire le fichier `analysis.md` complet

## 4. Prompt d'ingestion — Génération par fichier

- [x] 4.1 Générer le bloc Contexte + Références obligatoires (paths vers reference files, metadata)
- [x] 4.2 Générer T1 — Chargement et nettoyage (paramètres read_csv, regex guillemets, normalisation noms, parsing dates)
- [x] 4.3 Générer T2 — Agrégation sites (groupby SITE_AKG_ID, agrégation CARAC_*, BIBLIOGRAPHY, COMMENTS)
- [x] 4.4 Générer T3 — Classification (mapping CARAC_LVL1 → type_site, dates → périodes, scoring confiance)
- [x] 4.5 Générer T4 — Géocodage et projection (validation bounding box, projection EPSG:4326 → EPSG:2154, flag centroïdes)
- [x] 4.6 Générer T5 — Déduplication inter-sources (comparaison sites.csv + golden_sites.csv, distance < 500m, fuzzy name > 0.85)
- [x] 4.7 Générer T6 — Export (sites_cleaned.csv schéma normalisé, quality_report.json)
- [x] 4.8 Écrire le fichier `ingestion_prompt.md` complet

## 5. Relations inter-fichiers

- [x] 5.1 Comparer les schémas des deux fichiers (colonnes identiques, différences de remplissage)
- [x] 5.2 Analyser le recouvrement géographique (bounding boxes, sites proches < 1 km, doublons < 500m + même commune)
- [x] 5.3 Analyser la complémentarité chronologique (% de datations précises LoupBernard vs indéterminées ADAB2011)
- [x] 5.4 Analyser la complémentarité typologique (distribution CARAC_LVL1 par fichier)
- [x] 5.5 Identifier les correspondances avec golden_sites.csv et le sous-projet CAG Bas-Rhin
- [x] 5.6 Rédiger la stratégie de fusion recommandée (ordre d'ingestion, déduplication, enrichissement)
- [x] 5.7 Construire la matrice de correspondance des champs (ArkeoGIS LoupBernard / ADAB2011 / BaseFerRhin cible)
- [x] 5.8 Écrire le fichier `data/analysis/CROSS_FILE_RELATIONS.md`

## 6. Validation finale

- [x] 6.1 Vérifier que chaque dossier `data/analysis/<stem>/` contient bien 4 fichiers (metadata.json, analysis.md, ingestion_prompt.md, sample_data.csv)
- [x] 6.2 Vérifier que `data/analysis/CROSS_FILE_RELATIONS.md` existe et couvre les 7 sections requises
- [x] 6.3 Valider la cohérence des metadata.json (total_rows correspond au CSV, bounding box dans la zone Rhin supérieur)
- [x] 6.4 Relire les prompts d'ingestion pour s'assurer qu'ils sont auto-contenus et exécutables
