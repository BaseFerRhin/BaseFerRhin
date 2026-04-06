# Modèle de domaine

Le domaine couvre l'inventaire des sites archéologiques de l'**âge du Fer** (Hallstatt et La Tène) dans le **Rhin supérieur** : Alsace, Bade-Wurtemberg méridional et Canton de Bâle.

## Entités principales

```
Site 1───* PhaseOccupation
  │
  └──1───* Source
```

### Site (`src/domain/models/site.py`)

Entité racine de l'agrégat. Chaque site a un identifiant unique (`SITE-` + MD5), des coordonnées optionnelles, un type et une localisation administrative.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `site_id` | `str` | requis | `SITE-{md5(source_path\|page\|raw_text[:500])}` |
| `nom_site` | `str` | requis | Nom canonique du site |
| `variantes_nom` | `list[str]` | — | Variantes linguistiques (FR/DE) |
| `pays` | `Pays` | requis | `FR`, `DE`, `CH` |
| `region_admin` | `str` | requis | Grand Est, Baden-Württemberg, Basel-Stadt... |
| `commune` | `str` | requis | Commune canonique |
| `latitude` | `float?` | `[-90, 90]` | WGS84 |
| `longitude` | `float?` | `[-180, 180]` | WGS84 |
| `precision_localisation` | `PrecisionLocalisation` | requis | exact / approx / centroïde |
| `type_site` | `TypeSite` | requis | oppidum, habitat, nécropole... |
| `description` | `str?` | — | Texte descriptif libre |
| `surface_m2` | `float?` | `≥ 0` | Surface estimée |
| `altitude_m` | `float?` | — | Altitude |
| `statut_fouille` | `StatutFouille?` | — | fouille / prospection / signalement / archivé |
| `identifiants_externes` | `dict[str, str]` | — | Refs externes (ex : Patriarche) |
| `commentaire_qualite` | `str?` | — | Note qualité données |
| `phases` | `list[PhaseOccupation]` | — | Phases d'occupation |
| `sources` | `list[Source]` | — | Sources bibliographiques |
| `date_creation` | `datetime` | UTC auto | — |
| `date_maj` | `datetime` | UTC auto | — |

### PhaseOccupation (`src/domain/models/phase.py`)

Chaque phase lie un site à une période chronologique avec datation optionnelle.

| Champ | Type | Description |
|---|---|---|
| `phase_id` | `str` | Identifiant unique |
| `site_id` | `str` | FK vers Site |
| `periode` | `Periode` | Hallstatt / La Tène / Transition / indéterminé |
| `sous_periode` | `str?` | Ha C, Ha D1, LT B2, etc. |
| `datation_debut` | `int?` | Année BCE (ex: -650) |
| `datation_fin` | `int?` | Année BCE (ex: -450) |
| `methode_datation` | `str?` | Méthode (C14, typochronologie...) |
| `mobilier_associe` | `list[str]` | Mobilier associé |

**Validateur** `check_sub_period_consistency` : si `sous_periode` est définie, elle doit appartenir aux sous-périodes autorisées pour la période parente.

Sous-périodes autorisées :

| Période | Sous-périodes |
|---|---|
| Hallstatt | Ha C, Ha D, Ha D1, Ha D2, Ha D3, Ha D2-D3, Ha D2/D3 |
| La Tène | LT A, LT B, LT B1, LT B2, LT C, LT C1, LT C2, LT D, LT D1, LT D2 |
| Transition | Ha D3 / LT A, Ha D3/LT A |

### Source (`src/domain/models/source.py`)

Provenance de l'information avec indicateur de confiance.

| Champ | Type | Description |
|---|---|---|
| `source_id` | `str` | Identifiant unique |
| `site_id` | `str` | FK vers Site |
| `reference` | `str` | Référence bibliographique |
| `type_source` | `TypeSource?` | gallica_cag, publication, tableur... |
| `url` | `str?` | URL de la source |
| `ark_gallica` | `str?` | Identifiant ARK Gallica |
| `page_gallica` | `int?` | Numéro de page Gallica |
| `niveau_confiance` | `NiveauConfiance` | élevé / moyen / faible (défaut: moyen) |
| `confiance_ocr` | `float?` | `[0, 1]` — score qualité OCR |
| `date_extraction` | `datetime` | UTC auto |

### RawRecord (`src/domain/models/raw_record.py`)

Dataclass légère utilisée avant normalisation. Contient le texte brut et les champs pré-analysés.

| Champ | Type | Description |
|---|---|---|
| `raw_text` | `str` | Texte brut extrait |
| `commune` | `str?` | Commune détectée |
| `type_mention` | `str?` | Type de site brut |
| `periode_mention` | `str?` | Période brute |
| `latitude_raw` / `longitude_raw` | `float?` | Coordonnées brutes |
| `source_path` | `str` | Chemin du fichier source |
| `page_number` | `int?` | Numéro de page |
| `extraction_method` | `str` | `gallica_ocr`, `tesseract_iiif`, `csv`, `pdf` |
| `ark_id` | `str?` | ARK Gallica |
| `context_text` | `str?` | Contexte élargi |
| `extra` | `dict` | Champs supplémentaires |

## Énumérations (`src/domain/models/enums.py`)

### TypeSite (9 valeurs)

`oppidum`, `habitat`, `nécropole`, `dépôt`, `sanctuaire`, `atelier`, `voie`, `tumulus`, `indéterminé`

### Periode (4 valeurs)

`Hallstatt`, `La Tène`, `Hallstatt/La Tène`, `indéterminé`

### NiveauConfiance (3 valeurs)

`élevé`, `moyen`, `faible`

### PrecisionLocalisation (3 valeurs)

`exact`, `approx`, `centroïde`

### StatutFouille (4 valeurs)

`fouille`, `prospection`, `signalement`, `archivé`

### TypeSource (7 valeurs)

`gallica_cag`, `gallica_periodique`, `gallica_ouvrage`, `carte`, `tableur`, `publication`, `rapport_fouille`

### Pays (3 valeurs)

`FR`, `DE`, `CH`

## Normalisation (`src/domain/normalizers/`)

4 normaliseurs orchestrés par `SiteNormalizer` (composite).

### SiteNormalizer (`composite.py`)

Construit un `Site` + `PhaseOccupation` + `Source` à partir d'un `RawRecord`. Defaults : `Pays.FR`, `region_admin="Alsace"`, `nom_site = commune ou "Inconnu"`, `precision_localisation = EXACT si lat/lon, sinon CENTROIDE`.

### PeriodeNormalizer (`periode.py`)

Charge `data/reference/periodes.json` (patterns FR et DE). Recherche la période par substring match, extrait la sous-période via regex `sub_period_regex`. Fallback : préfixe `Ha` → Hallstatt, `LT` → La Tène, sinon `INDETERMINE`.

### ToponymeNormalizer (`toponymie.py`)

Charge `data/reference/toponymes_fr_de.json` (~30 entrées de concordance FR/DE). Retourne `(canonical, variantes)`.

### TypeSiteNormalizer (`type_site.py`)

Charge `data/reference/types_sites.json` (8 types × aliases FR/DE). Recherche par substring match. Collecte les termes non reconnus. Default `INDETERMINE`.

## Validation (`src/domain/validators/`)

### Cohérence chronologique (`coherence_chrono.py`)

Règles appliquées à chaque `PhaseOccupation` :
- `datation_debut > datation_fin` → warning
- Datation hors bornes de la période : Hallstatt `(-800, -450)`, La Tène `(-450, -25)`, Transition `(-500, -400)`
- Préfixe de sous-période incohérent avec la période (Hallstatt doit avoir `Ha`, La Tène doit avoir `LT`)

### Cohérence géographique (`coherence_geo.py`)

Bounding box du Rhin supérieur :

```
lat_min=47.0  lat_max=49.5
lon_min=6.5   lon_max=9.0
```

Warning si coordonnées hors de la zone.

## Déduplication (`src/domain/deduplication/`)

### Algorithme

1. **Scoring** (`SimilarityScorer`) — scoring pairwise de tous les sites
2. **Union-Find** — regroupement des paires avec score ≥ `merge_threshold` (défaut 0.85)
3. **Review queue** — paires entre `review_threshold` (0.70) et `merge_threshold`
4. **Merge** (`SiteMerger`) — fusion par cluster, triés par richesse de données

### Formule de scoring

| Cas | Formule |
|---|---|
| Les deux ont des coordonnées | `0.4·name_sim + 0.3·commune_sim + 0.3·geo_sim` |
| Aucun n'a de coordonnées | `0.7·name_sim + 0.3·commune_sim` |
| Un seul a des coordonnées | `(0.4·name_sim + 0.3·commune_sim) / 0.7` |

- `name_sim` = `rapidfuzz.fuzz.token_sort_ratio` / 100
- `commune_sim` = idem sur commune
- `geo_sim` = `1 - min(haversine_km, 50) / 50`

### Stratégie de merge

Le site le plus riche (plus de champs remplis) est le primaire. Fusion :
- Champs optionnels vides du primaire ← remplis par le secondaire
- `variantes_nom` ← union + nom secondaire si distinct
- `sources` ← union par `source_id`, reassignment du `site_id`
- `phases` ← dédoublonnage par clé JSON (contenu hors ids/timestamps)
- `identifiants_externes` ← merge dict
