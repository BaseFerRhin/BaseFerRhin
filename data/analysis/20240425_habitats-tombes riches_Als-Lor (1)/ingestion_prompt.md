# Prompt d’ingestion exécutable — Habitats et tombes riches (Als-Lor)

> **Objectif :** charger le classeur Excel, normaliser les toponymes et types, mapper les périodes, **dédupliquer sans coordonnées** par rapport à `sites.csv`, exporter `sites_cleaned.csv`.

---

## Contexte

- **Projet :** BaseFerRhin — Rhin supérieur (Alsace, Bade-Wurtemberg, Bâle).
- **Données :** 110 entrées, **21 colonnes**, **sans X/Y**. Tombes riches / habitats fortifiés, armement, or, chars, imports céramiques et métalliques. Chronologie **Hallstatt / La Tène**.
- **Fichier :** `data/input/20240425_habitats-tombes riches_Als-Lor (1).xlsx`

## Références obligatoires

| Fichier | Usage |
|---------|--------|
| `data/reference/types_sites.json` | OPPIDUM, HABITAT, NECROPOLE, TUMULUS, … |
| `data/reference/periodes.json` | HALLSTATT, LA_TENE, TRANSITION |
| `data/reference/toponymes_fr_de.json` | Concordance FR/DE des communes |
| `data/output/sites.csv` | Déduplication par nom / commune / pays |

---

## T1 — Chargement

```python
import pandas as pd

PATH = "data/input/20240425_habitats-tombes riches_Als-Lor (1).xlsx"

df = pd.read_excel(PATH, engine="openpyxl", header=0)
df.columns = df.columns.str.strip()
# Inspecter la 1ère ligne de données pour deviner le rôle de "Unnamed: 6" ; renommer ex. "complement_armement"
```

---

## T2 — Nettoyage

1. **`Pays`** : mapper `{"D": "DE", "d": "DE", "F": "FR", "f": "FR"}` ; compléter depuis `Dept/Land` si `Pays` vide (BW, RP, Bade-Wurtemberg → DE).
2. **`Dept/Land`** : conserver en champ `admin_raw` ; normaliser codes numériques français (54, 57, 67, 68).
3. **`Commune`, `Lieudit`** : strip, collapse espaces ; `NaN` pour cellules vides.
4. Pas de validation de coordonnées (absentes) ; créer `x_l93 = y_l93 = NaN`.
5. Option : détecter lignes entièrement vides et les retirer.

---

## T3 — Classification

1. **`type_site`** à partir de `type` (insensible à la casse, contient) :
   - `site fortifié`, `hauteur`, `oppidum` → **`oppidum`**
   - `tombe princière`, `tombe riche`, `char` → **`nécropole`** ou **`tumulus`** si le texte évoque tertre / tumulus (cf. alias `types_sites.json`)
2. **`periode` / `sous_periode`** : parser `Datation` puis `Datation globale Tum` en secours ; utiliser `patterns_fr` et `sub_period_regex` de `periodes.json`.
3. **Bronze** (« Bz moyen », etc.) : sortir dans `periode = "Bronze final"` ou `indéterminé` selon politique — **non couvert** par les clés HALLSTATT/LA_TENE seules.

---

## T4 — Projection

- **Non applicable** à la source (pas de L93).  
- Si géocodage ultérieur fournit L93, appliquer alors :

```python
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
# lon, lat = transformer.transform(x_l93, y_l93)
```

---

## T5 — Déduplication

1. Charger `sites.csv`.
2. Construire clé normalisée :  
   `slug = lower(strip(ascii_fold(commune))) + "|" + lower(strip(ascii_fold(nom_site))) + "|" + pays`
3. Comparer aux sites existants **sans seuil de distance** ; en cas de match, marquer `duplicate_of_site_id`.
4. Pour ambiguïtés (même commune, lieudits différents), **ne pas fusionner** automatiquement — flag `needs_review`.

---

## T6 — Export

Fichier **`sites_cleaned.csv`** :

Colonnes minimales suggérées :

`site_id,nom_site,commune,pays,type_site,x_l93,y_l93,longitude,latitude,periode,sous_periode,datation_debut,datation_fin,source_file,armement_summary,or_summary,remarques`

- Remplir `armement_summary` / `or_summary` par concaténation tronquée des colonnes sources si utile.
- `latitude` / `longitude` vides sauf géocodage externe.
- `source_file` : nom du xlsx.

---

## Critères de succès

- Pays et communes normalisés ; pas de `D`/`F` bruts en export final.
- Chaque `type_site` ∈ vocabulaire BaseFerRhin (minuscules cohérents avec `sites.csv`).
- Liste des **doublons potentiels** exportée (`dedup_report.csv`).

---

*Prompt autonome — BaseFerRhin.*
