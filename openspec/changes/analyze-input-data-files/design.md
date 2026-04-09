## Context

Le projet BaseFerRhin dispose de 2 fichiers CSV dans `data/input/`, tous deux exportés depuis la plateforme ArkeoGIS au format standard (22 colonnes, séparateur `;`) :

- **20250806_LoupBernard_ArkeoGis.csv** : 116 sites de l'âge du Fer du Bade-Wurtemberg (base de Loup Bernard), dominé par les enceintes/oppida, datations précises (Hallstatt/La Tène)
- **20250806_ADAB2011_ArkeoGis.csv** : 696 enregistrements de l'inventaire archéologique du Nordbaden (ADAB-2011), toutes périodes confondues, beaucoup de datations "Indéterminé"

Le modèle ArkeoGIS est **multi-lignes par site** : un même `SITE_AKG_ID` peut avoir N lignes, chacune décrivant une caractéristique (mobilier, immobilier, production) via la hiérarchie `CARAC_NAME → LVL1 → LVL2 → LVL3 → LVL4`.

Le projet dispose déjà de fichiers de référence normalisés : `periodes.json`, `types_sites.json`, `toponymes_fr_de.json`. Le pipeline ETL existant produit `data/output/sites.csv` et `data/output/sites.geojson`.

## Goals / Non-Goals

**Goals:**
- Produire une documentation complète et structurée pour chaque fichier d'entrée
- Générer des metadata JSON exploitables programmatiquement
- Définir le mapping exact entre le schéma ArkeoGIS et le modèle BaseFerRhin
- Identifier et documenter les relations entre les fichiers (recouvrement, complémentarité)
- Créer des prompts d'ingestion auto-contenus réutilisables par un agent IA

**Non-Goals:**
- Modifier le pipeline ETL existant (`src/`)
- Exécuter l'ingestion effective des données (c'est l'étape suivante)
- Ajouter de nouvelles dépendances Python au projet
- Traiter les fichiers hors `data/input/` (RawData, gallica, CAG Bas-Rhin)

## Decisions

### D1 — Script Python unique vs modules séparés

**Choix** : Un script Python unique `scripts/analyze_input_files.py` (~150 lignes) qui itère sur les fichiers de `data/input/`.

**Rationale** : Ce travail est un one-shot d'analyse, pas une fonctionnalité récurrente du pipeline. Un script unique est plus simple à exécuter et à comprendre qu'un module dans `src/`. Il utilise uniquement pandas + json (déjà disponibles).

**Alternative rejetée** : Intégrer l'analyse dans le pipeline ETL — trop couplé, l'analyse est un pré-requis à l'ingestion, pas une étape du pipeline.

### D2 — Structure de sortie : un dossier par fichier

**Choix** : `data/analysis/<stem>/` où `<stem>` est le nom du fichier sans extension. Chaque dossier contient 4 fichiers : `metadata.json`, `analysis.md`, `ingestion_prompt.md`, `sample_data.csv`.

**Rationale** : Isoler les analyses par fichier permet d'ajouter de nouveaux fichiers d'entrée sans toucher les analyses existantes. Le nom du dossier est déterministe et auto-documenté.

**Alternative rejetée** : Un seul fichier d'analyse global — perd la traçabilité par source et complique la maintenance.

### D3 — Metadata JSON : schéma orienté data profiling

**Choix** : Le metadata.json inclut du data profiling (null rates, unique counts, distributions) au-delà d'un simple dictionnaire de colonnes.

**Rationale** : Le profiling automatique permet de détecter les problèmes de qualité (centroïdes communaux, datations indéterminées, guillemets malformés) sans lecture manuelle. Il alimente directement le quality score.

### D4 — Mapping des types ArkeoGIS → BaseFerRhin via types_sites.json existant

**Choix** : Réutiliser le fichier de référence `data/reference/types_sites.json` existant pour le mapping `CARAC_LVL1 → type_site`. Les alias FR/DE couvrent déjà les termes ArkeoGIS (Enceinte, Habitat, Funéraire...).

**Rationale** : Évite de dupliquer la logique de classification. Le fichier de référence est la source de vérité du projet.

**Alternative rejetée** : Table de mapping ad hoc dans chaque prompt — créerait des incohérences si les types évoluent.

### D5 — Document inter-fichiers unique plutôt que matrice dans chaque analysis.md

**Choix** : Un fichier `data/analysis/CROSS_FILE_RELATIONS.md` dédié aux relations inter-fichiers, séparé des analyses individuelles.

**Rationale** : Les relations sont par nature inter-fichiers. Les intégrer dans chaque analyse individuelle forcerait de la duplication et compliquerait la mise à jour.

## Risks / Trade-offs

**[Guillemets malformés dans ADAB2011]** → Le fichier contient des patterns `""""` (guillemets doubles échappés incorrectement). Mitigation : le script de metadata détecte et log ces anomalies ; le prompt d'ingestion inclut un nettoyage regex explicite.

**[Biais du centroïde communal]** → ~60% des coordonnées dans ADAB2011 sont des centroïdes de commune (`CITY_CENTROID=Oui`), pas des positions de site. Mitigation : le metadata.json calcule le ratio centroïde, et le prompt d'ingestion attribue un score de confiance LOW aux centroïdes.

**[Datations indéterminées]** → La majorité des enregistrements ADAB2011 ont `STARTING_PERIOD=Indéterminé`. Mitigation : documenter ce biais dans l'analysis.md et permettre un filtrage à l'ingestion (ne garder que les lignes avec datation pour l'inventaire Fer).

**[Évolution des fichiers d'entrée]** → Si de nouveaux fichiers sont ajoutés dans `data/input/`, le script doit être ré-exécuté. Mitigation : le script est idempotent (écrase les analyses existantes) et détecte automatiquement tout CSV dans le dossier.
