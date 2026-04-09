## Why

Les fichiers CSV ArkeoGIS dans `data/input/` (LoupBernard + ADAB2011, ~810 lignes au total) sont la source primaire de sites archéologiques de l'âge du Fer pour le versant badois du projet BaseFerRhin. Actuellement, aucune documentation structurée ni pipeline d'ingestion n'existe pour ces fichiers. Sans analyse préalable (qualité, schéma, relations inter-fichiers), l'ingestion dans la base normalisée produira des données incohérentes, des doublons, et des pertes d'information.

## What Changes

- Création d'un dossier `data/analysis/<nom_fichier>/` pour chaque fichier CSV dans `data/input/`
- Génération automatique de metadata JSON (fiche technique : colonnes, types, stats, emprise géographique, chronologie, qualité)
- Rédaction d'un document d'analyse Markdown par fichier (schéma détaillé, modèle de données ArkeoGIS multi-lignes, mapping vers le modèle BaseFerRhin, stratégie d'ingestion, limites)
- Création d'un prompt d'ingestion exécutable par agent IA pour chaque fichier (tâches T1-T6 : chargement, nettoyage, agrégation, classification, géocodage, déduplication)
- Production d'un document de synthèse inter-fichiers identifiant les relations, recouvrements géographiques, complémentarités, et stratégie de fusion

## Capabilities

### New Capabilities
- `file-metadata-generation`: Analyse automatique d'un fichier CSV et génération d'une fiche metadata JSON (colonnes, types, null rates, emprise géo, chronologie, score qualité)
- `file-analysis-documentation`: Rédaction d'un document Markdown d'analyse complète par fichier (schéma, modèle de données, mapping vers le modèle cible, stratégie d'ingestion, limites)
- `ingestion-prompt-generation`: Génération d'un prompt structuré et exécutable pour l'ingestion d'un fichier dans la base normalisée BaseFerRhin
- `cross-file-relations`: Analyse des relations entre fichiers d'entrée (recouvrement géographique, complémentarité chronologique/typologique, stratégie de fusion, correspondance avec les sources existantes)

### Modified Capabilities

## Impact

- **Données** : Création de `data/analysis/` avec 2 sous-dossiers (LoupBernard, ADAB2011) + fichier de synthèse
- **Références** : Utilisation de `data/reference/periodes.json`, `types_sites.json`, `toponymes_fr_de.json` (lecture seule)
- **Pipeline** : Prépare le terrain pour l'ingestion effective (pas de modification du pipeline ETL existant)
- **Dépendances** : pandas (déjà indirectement disponible via geopandas dans pyproject.toml)
