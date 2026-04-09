# Prompt d’ingestion — Alsace_Basel_AF (âge du Fer)

**Usage :** donner ce document tel quel à un agent IA (ou à un développeur) pour exécuter le pipeline d’ingestion depuis la racine du dépôt `BaseFerRhin`. Tous les chemins sont relatifs à cette racine.

**Prérequis Python :** `pandas`, `openpyxl`, `pyproj` ; optionnel : `rapidfuzz` pour T5.

---

## Contexte

**Projet :** BaseFerRhin — inventaire des sites de l’âge du Fer du Rhin supérieur.

**Fichier source :** `data/input/Alsace_Basel_AF (1).xlsx`  
- **1083** lignes, **16** colonnes.  
- **Coordonnées** : colonnes **`x`**, **`y`** (texte à parser), **`epsg_coord`** = **4326** (WGS84) ou **25832** (ETRS89 / UTM 32N).  
- **`id_site`** : **1070** valeurs uniques — **agrégation obligatoire** pour obtenir au plus une fiche par site (jusqu’à **3** lignes par id).  
- **`decouverte_annee`** : année de découverte / mention, **pas** une datation archéologique.  
- La colonne **`date`** est une **date de fichier / mise à jour**, **à ne pas mapper** sur les phases Fer.

**Objectif :** charger, normaliser les SCR, reprojeter en Lambert-93, agréger par `id_site`, enrichir typologie/période si sources externes, dédupliquer, exporter CSV + rapport qualité.

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Types et alias. |
| `data/reference/periodes.json` | Fenêtres Hallstatt / La Tène / Transition. |
| `data/reference/toponymes_fr_de.json` | Noms de lieux FR ↔ DE. |
| `data/sources/golden_sites.csv` | Déduplication. |
| `data/analysis/Alsace_Basel_AF (1)/metadata.json` | Comptages, colonnes, EPSG observés. |

---

## Tâches

### T1 — Chargement et nettoyage

1.  
   ```python
   import pandas as pd
   df = pd.read_excel("data/input/Alsace_Basel_AF (1).xlsx", engine="openpyxl")
   ```
2. Vérifier **1083** lignes et les 16 colonnes attendues.  
3. Convertir `x`, `y` en `float` (virgule décimale si présente — gérer locale FR).  
4. `epsg_coord` : arrondir ou caster en int (4326 / 25832) ; lignes avec EPSG manquant → liste `epsg_missing` dans le rapport.  
5. Textes : `strip()` sur `commune`, `lieu_dit`, `pays`, `admin1`, références biblio.

### T2 — Agrégation par `id_site`

1. Grouper par **`id_site`** (cible **≤ 1070** groupes).  
2. Pour chaque groupe :
   - si une seule ligne → la conserver ;  
   - si plusieurs : fusionner `ref_biblio`, `ref_rapport`, `commentaire` (dédupliquer après strip) ;  
   - **coordonnées** : si toutes les lignes ont les mêmes (x,y,epsg) à tolérance numérique → une paire ; sinon privilégier la ligne **EPSG renseigné + cohérent** ou la plus récente selon règle documentée, et signaler `coordinate_conflict` dans le rapport.  
3. Ne pas agréger des `id_site` différents.

### T3 — Classification (période / type)

1. **Sans colonne période archéologique directe** : laisser `periode` / `datation_*` **vides** ou les remplir **uniquement** après jointure avec d’autres jeux (Patriarche, BdD Proto, etc.) — le documenter.  
2. Si `commentaire` ou `lieu_dit` contient des indices forts (ex. « Hallstatt », « La Tène »), appliquer **patterns** de `periodes.json` avec faible priorité et marquer `inferred_from_text=true` dans le rapport.  
3. `type_site` : idem — jointure externe préférable ; sinon heuristique documentée.

### T4 — Projections et validation géographique

1. Pour chaque ligne (puis chaque site agrégé), selon `epsg_coord` :
   - **4326** : `lon, lat = x, y`. Vérifier **lon** ∈ **[5, 11]** et **lat** ∈ **[45, 50]** (emprise Rhin sup. élargie) ; hors bornes → `coordinates_suspicious`.  
   - **25832** : transformer vers WGS84 puis vers **EPSG:2154** :
   ```python
   from pyproj import Transformer
   t_utm_to_l93 = Transformer.from_crs("EPSG:25832", "EPSG:2154", always_xy=True)
   x_l93, y_l93 = t_utm_to_l93.transform(x, y)
   ```
   Alternative : 25832 → 4326 → 2154 en deux étapes si plus lisible.  
2. Depuis WGS84 final, remplir `longitude`, `latitude` et `x_l93`, `y_l93`.  
3. `precision_localisation` : **point** si coordonnées issues du fichier ; ajuster si commentaire indique approximation.

### T5 — Déduplication inter-sources

1. Charger `data/output/sites.csv` et `data/sources/golden_sites.csv`.  
2. Matcher si **distance &lt; 500 m** (Haversine ou en L93) **et** commune normalisée compatible, **ou** fuzzy **token_sort_ratio ≥ 0,85** sur (`lieu_dit` ou `commune` + contexte).  
3. Utiliser `toponymes_fr_de.json` pour aligner variantes FR/DE.  
4. Consigner toutes les paires dans `quality_report.json`.

### T6 — Export

1. **CSV :** `data/analysis/Alsace_Basel_AF (1)/sites_cleaned.csv`  
   - Colonnes conseillées : `site_id`, `id_site_source`, `nom_site`, `commune`, `lieu_dit`, `pays`, `admin1`, `longitude`, `latitude`, `x_l93`, `y_l93`, `epsg_source`, `decouverte_annee`, `decouverte_operation`, `periode`, `sous_periode`, `datation_debut`, `datation_fin`, `type_site`, `confiance`, `source`, `bibliographie`, `rapports`, `commentaire`.  
   - `site_id` : ex. `ALSACE-BASEL-AF-{id_site}`.  
   - `source` : chaîne fixe, ex. `Alsace_Basel_AF_xlsx`.  
   - `bibliographie` : fusion `ref_biblio` + `ref_rapport` dédupliquée.

2. **Rapport :** `data/analysis/Alsace_Basel_AF (1)/quality_report.json`  
   - `row_count_raw` (1083), `site_count_aggregated` (≤ 1070)  
   - `epsg_missing`, `coordinates_suspicious`, `coordinate_conflicts`  
   - `duplicates_with_golden_or_sites_csv`  
   - `notes` : rappel **25832 vs 4326**, exclusion de `date` comme chrono archéo

---

## Validation (obligatoire)

1. Après agrégation : **au plus 1070** sites (un par `id_site`).  
2. Chaque site exporté avec paire (lon, lat) **ou** (x_l93, y_l93) cohérente ; aucune transformation sans EPSG connu (sauf règle d’exception documentée).  
3. Aucune utilisation de la colonne **`date`** comme datation Fer.  
4. Fichiers produits présents : `sites_cleaned.csv`, `quality_report.json`.

---

*Fin du prompt d’ingestion.*
