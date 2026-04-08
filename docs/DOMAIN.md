# Modèle de domaine

Le domaine couvre l'inventaire des sites archéologiques de l'**âge du Fer** (Hallstatt et La Tène) dans le **Rhin supérieur** : Alsace, Bade-Wurtemberg méridional et Canton de Bâle.

## Entités principales

```
Site 1───* PhaseOccupation
  │
  └──1───* Source
```

### Site (`src/domain/models/site.py`)

Entité racine de l'agrégat. Coordonnées en Lambert-93 (EPSG:2154) avec bornes validées.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `site_id` | `str` | requis | `SITE-{md5(source_path\|page\|raw_text[:500])}` |
| `nom_site` | `str` | requis | Nom canonique du site |
| `variantes_nom` | `list[str]` | — | Variantes linguistiques (FR/DE) |
| `pays` | `Pays` | requis | `FR`, `DE`, `CH` |
| `region_admin` | `str` | requis | Alsace, Baden-Württemberg... |
| `commune` | `str` | requis | Commune canonique |
| `x_l93` | `float?` | `[100 000, 1 200 000]` | Lambert-93 X (mètres) |
| `y_l93` | `float?` | `[6 000 000, 7 200 000]` | Lambert-93 Y (mètres) |
| `precision_localisation` | `PrecisionLocalisation` | requis | exact / approx / centroïde |
| `type_site` | `TypeSite` | requis | oppidum, habitat, nécropole... |
| `description` | `str?` | — | Texte descriptif libre |
| `surface_m2` | `float?` | `>= 0` | Surface estimée |
| `altitude_m` | `float?` | — | Altitude |
| `statut_fouille` | `StatutFouille?` | — | fouille / prospection / signalement / archivé |
| `identifiants_externes` | `dict[str, str]` | — | Patriarche EA, ArkeoGIS ID, Alsace-Basel ID |
| `commentaire_qualite` | `str?` | — | Note qualité données |
| `phases` | `list[PhaseOccupation]` | — | Phases d'occupation |
| `sources` | `list[Source]` | — | Sources bibliographiques |
| `date_creation` | `datetime` | UTC auto | — |
| `date_maj` | `datetime` | UTC auto | — |

### PhaseOccupation (`src/domain/models/phase.py`)

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

**Validateur** `check_sub_period_consistency` : la sous-période doit être compatible avec la période parente (préfixe Ha pour Hallstatt, LT pour La Tène).

### Source (`src/domain/models/source.py`)

| Champ | Type | Description |
|---|---|---|
| `source_id` | `str` | Identifiant unique |
| `site_id` | `str` | FK vers Site |
| `reference` | `str` | Référence bibliographique |
| `type_source` | `TypeSource?` | gallica_cag, tableur, publication... |
| `url` | `str?` | URL de la source |
| `ark_gallica` | `str?` | Identifiant ARK Gallica |
| `page_gallica` | `int?` | Numéro de page |
| `niveau_confiance` | `NiveauConfiance` | élevé / moyen / faible (défaut: moyen) |
| `confiance_ocr` | `float?` | `[0, 1]` — score qualité OCR |
| `date_extraction` | `datetime` | UTC auto |

### RawRecord (`src/domain/models/raw_record.py`)

Dataclass légère (pré-normalisation). Transporte le texte brut et les champs pré-analysés par les extracteurs.

| Champ | Type | Description |
|---|---|---|
| `raw_text` | `str` | Texte brut extrait |
| `commune` | `str?` | Commune détectée |
| `type_mention` | `str?` | Type de site brut |
| `periode_mention` | `str?` | Période brute |
| `latitude_raw` / `longitude_raw` | `float?` | Coordonnées WGS84 brutes |
| `source_path` | `str` | Chemin du fichier source |
| `page_number` | `int?` | Numéro de page |
| `extraction_method` | `str` | Identifiant de l'extracteur |
| `ark_id` | `str?` | ARK Gallica |
| `context_text` | `str?` | Contexte élargi |
| `extra` | `dict` | Champs spécifiques à chaque extracteur |

Le champ `extra` transporte des données structurées propres à chaque source : `patriarche_ea`, `SITE_AKG_ID`, `phases_bool`, `x_l93`/`y_l93` (Lambert-93 natif), `lieu_dit`, `pays`, `datation_debut`/`datation_fin`, `epsg_source`, `chrono_dbf`, etc.

## Énumérations (`src/domain/models/enums.py`)

| Enum | Valeurs |
|---|---|
| `TypeSite` (9) | oppidum, habitat, nécropole, dépôt, sanctuaire, atelier, voie, tumulus, indéterminé |
| `Periode` (4) | Hallstatt, La Tène, Hallstatt/La Tène, indéterminé |
| `NiveauConfiance` (3) | élevé, moyen, faible |
| `PrecisionLocalisation` (3) | exact, approx, centroïde |
| `StatutFouille` (4) | fouille, prospection, signalement, archivé |
| `TypeSource` (7) | gallica_cag, gallica_periodique, gallica_ouvrage, carte, tableur, publication, rapport_fouille |
| `Pays` (3) | FR, DE, CH |

## Normalisation (`src/domain/normalizers/`)

6 normaliseurs orchestrés par `SiteNormalizer` (composite).

### SiteNormalizer (`composite.py`)

Construit un `Site` + `PhaseOccupation` + `Source` à partir d'un `RawRecord` :

1. Normalise le type de site via `TypeSiteNormalizer`
2. Normalise la période et sous-période via `PeriodeNormalizer`
3. Normalise la commune via `ToponymeNormalizer`
4. Reprojette les coordonnées :
   - Priorité aux coords L93 natives dans `extra["x_l93"]`/`extra["y_l93"]` (nécropoles, inhumations, Alsace-Basel)
   - Sinon reprojection WGS84 → L93 via `wgs84_to_l93()`
5. Propage les identifiants externes (Patriarche EA, ArkeoGIS ID, Alsace-Basel ID) dans `identifiants_externes`
6. Détermine la précision de localisation depuis `extra["precision_localisation"]`
7. Détermine le pays depuis `extra["pays"]` (FR par défaut)

### DatationParser (`datation_parser.py`)

Parser unifié pour les formats de datation hétérogènes : intervalles numériques, labels textuels composites (« BF3/Ha C – LT A »), sous-périodes fractionnées.

### PeriodeNormalizer (`periode.py`)

Charge `data/reference/periodes.json` (patterns FR et DE). Recherche par substring, extrait la sous-période via regex. Fallback : préfixe Ha → Hallstatt, LT → La Tène, sinon indéterminé.

### ToponymeNormalizer (`toponymie.py`)

Concordance FR/DE via `data/reference/toponymes_fr_de.json` (~30 entrées). Retourne `(canonical, variantes)`.

### TypeSiteNormalizer (`type_site.py`)

Charge `data/reference/types_sites.json` (9 types × aliases FR/DE, y compris variantes allemandes : Siedlung, Grabhügel, Oppidum...). Collecte les termes non reconnus. Default `INDETERMINE`.

## Filtrage chronologique et géographique (`src/domain/filters/`)

### `chrono_filter.py`

Appliqué après INGEST pour ne retenir que les records pertinents à l'âge du Fer :

```
is_age_du_fer(record) :
  ├── Regex Fer (Hallstatt, La Tène, eisenzeit, protohistor…) → True
  ├── Phases booléennes (HaD, LTAB…) dans extra → True
  ├── Datation mentions dans extra → True
  ├── Dates numériques : fin <= -800 → False (Bronze pur)
  ├── Dates numériques : début > -25 → False (post-Romain)
  ├── Dates numériques : overlap [-800, -25] → True
  ├── Texte "âge du Bronze" sans mention Fer → False
  ├── Méthodes de confiance (patriarche, bdd_proto…) → True
  └── Sinon → False
```

Le filtre géographique exclut par département et/ou pays via `FilterConfig` dans `config.yaml`.

Logging par source : nombre total, retenus, exclus chrono, exclus géo.

## Validation (`src/domain/validators/`)

### Cohérence chronologique (`coherence_chrono.py`)

- `datation_debut > datation_fin` → warning
- Datation hors bornes : Hallstatt (-800, -450), La Tène (-450, -25)
- Préfixe sous-période incohérent (Ha ≠ LT)

### Cohérence géographique (`coherence_geo.py`)

Bounding box Rhin supérieur (Lambert-93) :

```
x: [930 000, 1 060 000]
y: [6 710 000, 6 990 000]
```

## Déduplication (`src/domain/deduplication/`)

### Algorithme en 4 phases

1. **Exact ID match** — Patriarche EA ou ArkeoGIS ID identique → score = 1.0
2. **Scoring pairwise** (`SimilarityScorer`) — rapidfuzz + distance L93
3. **Union-Find** — clusters avec score >= `merge_threshold` (0.85)
4. **Merge** (`SiteMerger`) — fusion par richesse de données

### Formule de scoring

| Cas | Formule |
|---|---|
| IDs externes identiques | `1.0` (court-circuit) |
| Deux sites avec coordonnées | `0.4·name + 0.3·commune + 0.3·geo` |
| Aucun avec coordonnées | `0.7·name + 0.3·commune` |
| Un seul avec coordonnées | `(0.4·name + 0.3·commune) / 0.7` |

- `name_sim` = `rapidfuzz.fuzz.token_sort_ratio / 100`
- `commune_sim` = idem sur la commune
- `geo_sim` = `1 - min(distance_L93_km, 50) / 50`
- Pénalité centroïde : `geo_sim *= 0.5` si un site a `precision = centroïde`

### Stratégie de merge

Le site le plus riche est le primaire. Fusion :
- Champs optionnels vides du primaire ← remplis par le secondaire
- `variantes_nom` ← union + nom secondaire si distinct
- `sources` ← union par `source_id`
- `phases` ← dédoublonnage par contenu JSON
- `identifiants_externes` ← merge dicts

## Reprojection (`src/infrastructure/geocoding/reprojector.py`)

Le `Reprojector` gère la reprojection multi-EPSG vers Lambert-93 :

- Cache interne des `Transformer` pyproj par EPSG source
- Validation entrées : NaN, inf, Null Island (0,0) → `ValueError`
- Vérification bounds L93 sur le résultat
- Méthode safe : `to_lambert93_safe()` retourne `(None, None, False)` en cas d'erreur
