# Prompt d’ingestion exécutable — Mobilier des sépultures (ODS)

> **Objectif :** lire le fichier ODS, nettoyer, classifier, projeter L93→WGS84 si besoin, agréger/dédoublonner vs `sites.csv`, exporter `sites_cleaned.csv` (+ optionnel détail sépultures).

---

## Contexte

- **Projet :** BaseFerRhin.
- **Données :** 310 sépultures, 91 colonnes, **coordonnées Lambert-93 sur toutes les lignes**, mobilier et pratiques funéraires détaillés.
- **Fichier :** `data/input/20240425_mobilier_sepult_def (1).ods`

## Références obligatoires

| Fichier | Usage |
|---------|--------|
| `data/reference/types_sites.json` | NECROPOLE, TUMULUS, etc. |
| `data/reference/periodes.json` | HALLSTATT, LA_TENE, TRANSITION |
| `data/reference/toponymes_fr_de.json` | Normalisation communes |
| `data/output/sites.csv` | Déduplication |

---

## T1 — Chargement

```python
import pandas as pd

PATH = "data/input/20240425_mobilier_sepult_def (1).ods"

# Nécessite odfpy : pip install odfpy
df = pd.read_excel(PATH, engine="odf", header=0)

# Normaliser noms de colonnes
df.columns = (
    df.columns.str.strip()
    .str.replace("Posiiton", "Position", regex=False)
    .str.replace("Offande secondaire", "Offrande secondaire", regex=False)
)
```

- Si `engine="odf"` indisponible : convertir en xlsx/csv hors pipeline puis `read_excel` / `read_csv`.

---

## T2 — Nettoyage

1. Supprimer les colonnes **100 % NA** (`Fer Brassard`, `AC Vaisselle`, …).
2. Convertir `Coordonnées x (Lambert 93)` et `Coordonnées y (Lambert 93)` en `float64`.
3. Valider plages L93 (repérer valeurs aberrantes).
4. `Commune`, `lieu-dit` : texte propre ; `N° Sep` en string pour préserver les zéros éventuels.

---

## T3 — Classification

1. **`type_site`** : valeur canonique **`nécropole`** (alias `inhumation`, `sépulture`).
2. **`periode` / `sous_periode`** : parser `chrono` (Ha D3, LT A, Ha D-LT A ?, …) avec `periodes.json` et regex `sub_period_regex`.
3. **`pays`** : `FR` par défaut ; ajuster si ligne hors France.

---

## T4 — Projection (Lambert-93 → WGS84)

```python
from pyproj import Transformer
import pandas as pd

transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

def row_to_wgs84(row):
    x = row["Coordonnées x (Lambert 93)"]
    y = row["Coordonnées y (Lambert 93)"]
    if pd.isna(x) or pd.isna(y):
        return pd.Series({"longitude": None, "latitude": None})
    lon, lat = transformer.transform(float(x), float(y))
    return pd.Series({"longitude": lon, "latitude": lat})
```

- Conserver **x_l93, y_l93** dans l’export principal (comme `sites.csv`).

---

## T5 — Déduplication

1. **Agrégation site** (avant comparaison au référentiel) :  
   - Clé `site_cluster = round(x, -1)` + `round(y, -1)` **ou** `commune_norm + "|" + lieudit_norm`  
   - Choisir un représentant par cluster (première ligne ou centroïde moyen des XY).
2. Charger `sites.csv` ; comparer avec **distance euclidienne L93** < seuil (ex. **25–50 m**) + proximité toponymique.
3. Marquer `match_site_id` ou `new_site`.

---

## T6 — Export

1. **`sites_cleaned.csv`** — une ligne par **site agrégé** :  
   `site_id,nom_site,commune,pays,type_site,x_l93,y_l93,longitude,latitude,periode,sous_periode,source_file,nb_sepultures`

   - `nb_sepultures` = nombre de lignes ODS dans le cluster.

2. **`sepultures_mobilier_detail.csv`** (recommandé) — grain 310 : conserver `N° Sep`, comptages mobilier clés, `chrono`, `Genre`, pour analyses.

---

## Critères de succès

- Colonnes vides retirées ou ignorées.
- Toutes les coordonnées valides ou signalées.
- Pas de double comptage du même site cartographique après agrégation.
- Périodes alignées sur `periodes.json` lorsque `chrono` est parseable.

---

*Prompt autonome — BaseFerRhin.*
