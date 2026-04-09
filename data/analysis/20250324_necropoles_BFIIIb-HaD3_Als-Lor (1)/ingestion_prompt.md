# Prompt d’ingestion exécutable — Nécropoles BF IIIb – Ha D3 (Als-Lor)

> **Objectif :** charger l’inventaire des nécropoles, normaliser les phases et coordonnées, mapper vers les référentiels, **fusionner intelligemment** avec `sites.csv` (déjà partiellement alimenté par ce fichier), exporter `sites_cleaned.csv`.

---

## Contexte

- **Projet :** BaseFerRhin — Rhin supérieur.
- **Données :** 339 nécropoles, 37 colonnes, **Lambert-93 systématique**, Alsace-Lorraine, **transition tertres / tombes plates**, **BF IIIb – Hallstatt D3**.
- **Fichier :** `data/input/20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx`

## Références obligatoires

| Fichier | Usage |
|---------|--------|
| `data/reference/types_sites.json` | NECROPOLE, TUMULUS, alias tertre / tumulus / enclos funéraire |
| `data/reference/periodes.json` | HALLSTATT, LA_TENE, TRANSITION ; sous-périodes Ha C–D3, LT A… |
| `data/reference/toponymes_fr_de.json` | Communes |
| `data/output/sites.csv` | **Déduplication et mise à jour** (fichier déjà référencé dans `source_references`) |

---

## T1 — Chargement

```python
import pandas as pd

PATH = "data/input/20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx"

df = pd.read_excel(PATH, engine="openpyxl", header=0)
df = df.rename(columns={"Unnamed: 0": "row_index"})
df.columns = df.columns.str.strip()
```

---

## T2 — Nettoyage

1. **`Coordonnées x/y`** : convertir en `float` ; détecter outliers (ex. Y < 6_000_000 ou X hors emprise Alsace-Lorraine élargie) → `coord_quality=bad` pour revue manuelle.
2. **`Nom`** : si valeur dans `{"non localisé", "non localise"}` (insensible casse), remplacer `nom_site` proposé par `Commune` + suffixe « nécropole » ou laisser vide avec flag.
3. **Colonnes phase** : normaliser cellules `-`, vide, `1`, `oui`, nombres → entier 0/1 ou NaN.
4. **`Dept`** : int → str pour cohérence export.
5. **`Date de fouille/découverte`** : conserver comme métadonnée (pas `periode` archéologique).

---

## T3 — Classification

1. **`type_site`** :  
   - défaut **`nécropole`**  
   - si `Tertre (élévation)` ou `Tertre arasé` actif et politique métier = distinguer **`tumulus`** (alias dans `types_sites.json`), sinon garder nécropole.

2. **`periode` / `sous_periode`** :  
   - Lire `Datation` et `Occupation nécropole` avec `patterns_fr` / regex du JSON.  
   - Pour chaque colonne du type `Hallstatt C1 (800-660)` etc., si marquée « 1 », émettre une phase **Hallstatt / Ha C1** (borne dates optionnelle depuis l’intitulé de colonne).  
   - **Bz** / **Protohistoire** : si détecté, `periode` = `Bronze final` ou `indéterminé` (hors enum stricte — documenter).

3. **`pays`** : `FR`.

---

## T4 — Projection (Lambert-93 → WGS84)

```python
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

def to_wgs84(x, y):
    lon, lat = transformer.transform(float(x), float(y))
    return lon, lat
```

Ajouter colonnes `longitude`, `latitude` dans l’export si nécessaire pour cartographie ; conserver **obligatoirement** `x_l93`, `y_l93`.

---

## T5 — Déduplication

1. Charger `sites.csv` ; isoler les lignes dont `source_references` contient déjà ce nom de fichier xlsx.
2. Pour chaque ligne du nouveau jeu :  
   - chercher match par **distance L93 < 30–80 m** ET `commune` normalisée proche ;  
   - ou par **égalité stricte** commune + nom de site normalisé.
3. Si match : **mettre à jour** `source_references` / enrichir phases plutôt que créer un `site_id` dupliqué.
4. Produire `ingest_report.csv` : `action` ∈ {`new`, `merge`, `skip_duplicate`, `review`}.

---

## T6 — Export

**`sites_cleaned.csv`** — schéma aligné sur `sites.csv` :

Colonnes types :  
`site_id,nom_site,commune,pays,type_site,x_l93,y_l93,longitude,latitude,phase_id,periode,sous_periode,datation_debut,datation_fin,sources_count,source_references,occupation_necropole_raw,chronologie_comment`

- **`phase_id`** : une ligne par **phase** détectée si le modèle cible est multi-phase (comme l’existant) ; sinon une ligne par site avec `periode` agrégée (moins recommandé).
- **`source_references`** : inclure le chemin absolu ou relatif du xlsx + `biblio`.
- Conserver une copie brute optionnelle `necropoles_BFIIIb_raw.parquet` pour traçabilité.

---

## Critères de succès

- Aucune coordonnée aberrante non flaggée.
- Phases Hallstatt cohérentes avec `periodes.json` lorsque les colonnes binaires sont utilisées.
- Fusions avec `sites.csv` tracées ; pas de duplication géographique évidente.
- Sites « non localisé » gérés explicitement (nom ou flag).

---

*Prompt autonome — BaseFerRhin.*
