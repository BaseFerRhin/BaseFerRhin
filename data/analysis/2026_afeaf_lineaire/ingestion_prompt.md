# Prompt d’ingestion — `2026_afeaf_lineaire.dbf` (agent exécutable)

Tu es un agent de données chargé d’ingérer la table **AFEAF linéaire** dans le cadre du projet **BaseFerRhin** (inventaire de l’âge du Fer du Rhin supérieur). Exécute les tâches de bout en bout et documente les hypothèses sur les colonnes **a–h**.

---

## Contexte

- **Projet** : BaseFerRhin — harmonisation d’inventaires protohistoriques pour analyse spatiale et croisement de sources.
- **Fichier source** : `data/input/2026_afeaf_lineaire.dbf`
- **Format** : **DBF**, **9 colonnes**, encodage attendu **latin-1**, **27 lignes**.
- **Identifiant** : `id` (unique, une ligne par id).
- **Particularité** : noms de champs **génériques** (`a` … `h`) ; sémantique inférée : pays, département, commune, lieu-dit, catégorie, chronologie, descriptions. **Géométrie** probablement dans un **.shp** homonyme — à localiser sous `data/input/` ou auprès du dépôt de données.
- **Qualité** : remplissage **100 %** ; vigilance **mojibake** sur accents (ex. La Tène).
- **Référence** : `data/analysis/2026_afeaf_lineaire/metadata.json`

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Codes canoniques et alias FR/DE pour les types de sites. |
| `data/reference/periodes.json` | Normalisation Hallstatt / La Tène / transition et patterns de matching. |
| `data/reference/toponymes_fr_de.json` | Concordance des toponymes communaux et variantes. |
| `data/analysis/2026_afeaf_lineaire/metadata.json` | Schéma et statistiques des colonnes. |
| `data/sources/golden_sites.csv` | Contrôle qualité et déduplication si présent dans le dépôt. |

---

## Tâches

### T1 — Chargement et normalisation texte

1. Lire le DBF avec encodage **latin-1** ; si caractères aberrants systématiques, tester **utf-8** sur un sous-échantillon et documenter l’encodage retenu dans `quality_report.json`.
2. Appliquer `strip()` sur toutes les colonnes texte.
3. Créer une table de correspondance **documentée** `a→pays`, `b→departement`, `c→commune`, `d→lieu_dit`, `e→categorie_courte`, `f→chrono_brut`, `g→description`, `h→detail` (ajuster si le producteur fournit un dictionnaire officiel).
4. Vérifier l’existence d’un fichier géométrique **même préfixe** (`2026_afeaf_lineaire.shp` ou équivalent) ; si trouvé, charger et conserver le lien `id` ↔ géométrie.

### T2 — Structuration chronologique

1. Parser `f` pour : dates **C14** (motifs type `cal BC`, plages numériques), libellés **La Tène** / **Hallstatt** / phases (Ha D, LT D1, etc.).
2. Produire des colonnes dérivées : `chrono_texte_normalise`, `periode_candidate`, `sous_periode_candidate`, `borne_debut`, `borne_fin` (nullable) en t’appuyant sur `periodes.json`.
3. Lorsque seule une mention qualitative existe, ne pas forcer de bornes numériques — laisser `null` et noter dans le rapport.

### T3 — Classification type de site

1. À partir de `e` : mapper « habitat » → **HABITAT** ; « indice de site » → code **INDETERMINE** ou règle projet équivalente, **documentée**.
2. Enrichir avec mots-clés français dans `g`/`h` (silo, fosse, nécropole, enceinte, voie, tumulus, etc.) vers `types_sites.json` (`aliases.fr`).
3. En cas de conflit entre `e` et le texte, appliquer une **priorité documentée** (ex. texte détaillé > catégorie courte).

### T4 — Géoréférencement

1. Si géométrie disponible : reprojeter en **WGS84** (lon/lat) et **Lambert-93** (EPSG:2154) ; pour les lignes, calculer au minimum **point représentatif** (centroïde ou milieu) pour l’intégration dans un schéma site-punctuel, **sans perdre** la géométrie ligne dans une couche dédiée si le modèle le permet.
2. Si pas de géométrie : exporter avec `longitude`/`latitude` vides et **flag** `spatial_status=no_geometry`.
3. Valider que les communes (`c`) sont cohérentes avec les départements (`b`) pour le périmètre **67/68**.

### T5 — Déduplication et rattachement

1. Comparer aux sites existants dans `data/output/sites.csv` (si présent) et `golden_sites.csv` : même commune + lieu-dit proche (normalisation via `toponymes_fr_de.json`) et/ou distance &lt; seuil métrique si coordonnées disponibles.
2. Lister dans `quality_report.json` les **matches probables** et les **isolats**.

### T6 — Export

1. Produire **`data/analysis/2026_afeaf_lineaire/sites_cleaned.csv`** (ou `linear_features_cleaned.csv` si le projet distingue lignes et points) avec au minimum :  
   `site_id`, `nom_site`, `commune`, `departement`, `pays`, `type_site`, `longitude`, `latitude`, `x_l93`, `y_l93`, `periode`, `sous_periode`, `datation_debut`, `datation_fin`, `confiance`, `source`, `description`, `detail`, `id_source_afeaf`  
   — adapter `site_id` (ex. préfixe `AFEAF_LIN_` + `id`).
2. Produire **`data/analysis/2026_afeaf_lineaire/quality_report.json`** : encodage, présence géométrie, comptages, règles de mapping a–h, anomalies.

---

## Validation

- **27** lignes lues, **27** `id` uniques.
- Aucune perte de ligne entre source et export.
- Rapport listant explicitement si la **géométrie** était disponible ou non.

À la fin, résume en **français** : lignes exportées, taux avec coordonnées, principaux types et avertissements.
