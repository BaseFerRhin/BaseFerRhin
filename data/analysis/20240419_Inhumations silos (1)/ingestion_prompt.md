# Prompt d’ingestion exécutable — Inhumations en silos

> **Objectif :** charger `20240419_Inhumations silos (1).xlsx`, nettoyer, classifier, projeter si besoin, dédupliquer par rapport à `data/output/sites.csv`, exporter un CSV normalisé.

---

## Contexte

- **Projet :** BaseFerRhin — inventaire archéologique protohistorique du Rhin supérieur (Alsace, Bade-Wurtemberg, Bâle).
- **Jeu de données :** 86 inhumations en silos, 94 colonnes, coordonnées **Lambert-93** (`X(L93)`, `Y(L93)`), contexte Alsace-Lorraine, transition Bronze final / Hallstatt — La Tène.
- **Fichier source :** `data/input/20240419_Inhumations silos (1).xlsx` (ou copie locale équivalente).

## Références obligatoires (à charger en code)

| Fichier | Usage |
|---------|--------|
| `data/reference/types_sites.json` | Alias FR/DE → types canoniques : OPPIDUM, HABITAT, NECROPOLE, DEPOT, SANCTUAIRE, ATELIER, VOIE, TUMULUS |
| `data/reference/periodes.json` | HALLSTATT (-800/-450), LA_TENE (-450/-25), TRANSITION ; sous-périodes Ha C, Ha D1, Ha D2, Ha D3, LT A… |
| `data/reference/toponymes_fr_de.json` | Normalisation des noms de communes / lieux (variantes FR/DE) |
| `data/output/sites.csv` | Référence pour **déduplication** et alignement de schéma |

---

## T1 — Chargement

```python
import pandas as pd

PATH = "data/input/20240419_Inhumations silos (1).xlsx"

df = pd.read_excel(
    PATH,
    engine="openpyxl",
    header=0,
    dtype=str,  # optionnel : tout en str puis cast ciblé
)
# Renommer colonnes : supprimer espaces superflus, remplacer "Précision \nâge" -> "Précision age"
df.columns = df.columns.str.replace(r"\s+", " ", regex=True).str.strip()
```

- Si `openpyxl` indisponible : `engine="calamine"` via `pd.read_excel` (pandas ≥ 2.2) ou conversion intermédiaire.
- Vérifier qu’une seule feuille est utilisée ; si multi-feuilles, spécifier `sheet_name=0` ou le nom exact.

---

## T2 — Nettoyage

1. **Supprimer les lignes agrégées** : filtrer où `Département == "TOTAL"` ou `Site` / `Lieu dit` contiennent « TOTAL » (insensible à la casse).
2. **Coordonnées** : convertir `X(L93)` et `Y(L93)` en `float` ; lignes avec les deux NaN : conserver mais `has_coords=False`.
3. **Plausibilité L93 (France métro approx.)** : ex. X ∈ [900_000, 1_300_000], Y ∈ [6_100_000, 7_200_000] — marquer `coord_flag` si hors plage.
4. **Colonnes parasites** : ignorer ou renommer `Unnamed: 93` en `notes_datation` si utile.
5. **Valeurs textuelles** : remplacer cellules vides Excel (`" "`, chaînes vides) par `NaN` sur colonnes clés.

---

## T3 — Classification

1. **`type_site` (canonique minuscule comme dans sites.csv, ex. `nécropole`, `habitat`)**  
   - Règle par défaut pour inhumation en silo sur habitat : **`habitat`** (alias `silo`, `structure d'habitat`) ou **`nécropole`** si la politique métier privilégie l’aspect funéraire — **choisir une règle unique documentée**.  
   - Croiser avec `types_sites.json` (`aliases` fr/de).

2. **`periode` / `sous_periode`**  
   - Parser `Datation relative` (et si besoin `14C (2 sigma)`) avec motifs de `periodes.json` (`patterns_fr`, `sub_period_regex`).  
   - Mapper vers : `Hallstatt`, `La Tène`, `indéterminé`, etc. et sous-périodes `Ha D3`, `LT A`, …

3. **`pays`** : `FR` pour départements français (67, 68, 57, 54…).

4. **`commune` / `nom_site`** : construire `nom_site = Site` ; enrichir avec `Lieu dit` si distinct ; normaliser via `toponymes_fr_de.json`.

---

## T4 — Projection (Lambert-93 → WGS84)

Si le pipeline doit produire `longitude` / `latitude` en plus de L93 :

```python
from pyproj import Transformer

transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

def l93_to_wgs84(x, y):
    if pd.isna(x) or pd.isna(y):
        return None, None
    lon, lat = transformer.transform(float(x), float(y))
    return lon, lat
```

Le fichier `sites.csv` actuel conserve **x_l93, y_l93** : la projection n’est **obligatoire** que pour export cartographique WGS84.

---

## T5 — Déduplication

1. Charger `sites.csv` existant.
2. **Agréger les lignes source par site** : clé proposée  
   `normalize(commune)` + `normalize(nom_site)` + arrondi `X,Y` (ex. 1 m) ou sans coords si absent.
3. Pour chaque groupe agrégé, comparer aux sites existants :  
   - même commune + distance L93 < **seuil** (ex. 50–100 m) **ou** même nom normalisé si pas de coords côté nouveau.
4. Marquer : `match_existing_site_id` / `is_new` / `merge_candidate`.

---

## T6 — Export

Produire **`sites_cleaned.csv`** (ou chemin dédié sous `data/output/ingest/`) avec colonnes alignées sur le schéma cible, par exemple :

`site_id,nom_site,commune,pays,type_site,x_l93,y_l93,longitude,latitude,periode,sous_periode,datation_debut,datation_fin,source_file,row_count_in_source,notes`

- Pour ce fichier **inhumations**, inclure `row_count_in_source` = nombre d’individus agrégés par site.
- `source_file` : chemin ou nom du xlsx source.
- Conserver une **table séparée** optionnelle `inhumations_silos_detail.csv` au grain individuel (86 lignes) pour ne pas perdre l’anthropologie.

---

## Critères de succès

- Aucune ligne `TOTAL` dans l’export site.
- Coordonnées validées ou explicitement absentes.
- Types et périodes issus des **référentiels JSON** lorsque le texte source correspond.
- Journal des fusions / doublons avec `sites.csv` écrit (log ou colonne).

---

*Prompt autonome — à exécuter dans l’environnement Python du dépôt BaseFerRhin.*
