# Prompt — Analyse des fichiers d'entrée `data/input/`

## Objectif

Analyser **chaque fichier** présent dans `data/input/`, produire une documentation structurée dans `data/analysis/<nom_fichier>/`, et identifier les relations inter-fichiers pour préparer l'ingestion dans la base BaseFerRhin.

---

## Fichiers à analyser

| Fichier | Lignes | Source | Couverture géographique |
|---|---|---|---|
| `20250806_LoupBernard_ArkeoGis.csv` | 117 (116 data + header) | ArkeoGIS — Loup Bernard | Bade-Wurtemberg (DE) |
| `20250806_ADAB2011_ArkeoGis.csv` | 697 (696 data + header) | ArkeoGIS — ADAB 2011 (Nordbaden) | Nord-Bade (DE) |

Les deux fichiers partagent le **même schéma ArkeoGIS** (22 colonnes, séparateur `;`).

---

## Instructions par fichier

Pour **chaque** fichier `<FILENAME>` dans `data/input/` :

### 1. Créer le dossier d'analyse

```
data/analysis/<FILENAME>/
├── metadata.json
├── analysis.md
├── ingestion_prompt.md
└── sample_data.csv        (optionnel : 20 premières lignes)
```

> `<FILENAME>` = nom du fichier sans extension (ex: `20250806_LoupBernard_ArkeoGis`)

### 2. `metadata.json` — Fiche technique du fichier

Générer un JSON avec les champs suivants :

```json
{
  "file_name": "20250806_LoupBernard_ArkeoGis.csv",
  "file_path": "data/input/20250806_LoupBernard_ArkeoGis.csv",
  "format": "CSV",
  "separator": ";",
  "encoding": "UTF-8",
  "header_row": true,
  "total_rows": 116,
  "total_columns": 22,
  "columns": [
    {
      "name": "SITE_AKG_ID",
      "type": "integer",
      "description": "Identifiant unique ArkeoGIS du site",
      "nullable": false,
      "unique_values": "<nombre>",
      "sample_values": ["25820", "25821", "25822"]
    }
  ],
  "source": {
    "platform": "ArkeoGIS",
    "database_name": "<valeur extraite de DATABASE_NAME>",
    "export_date": "2025-08-06",
    "author": "<auteur ou institution>",
    "license": "non spécifiée"
  },
  "geographic": {
    "projection": "EPSG:4326 (WGS84)",
    "bounding_box": {
      "min_lat": "<valeur>",
      "max_lat": "<valeur>",
      "min_lon": "<valeur>",
      "max_lon": "<valeur>"
    },
    "countries": ["DE"],
    "regions": ["Bade-Wurtemberg"],
    "city_centroid_ratio": "<% de lignes avec CITY_CENTROID=Oui>"
  },
  "chronology": {
    "date_format": "ArkeoGIS (-YYYY:-YYYY)",
    "period_range": {
      "earliest": "<date la plus ancienne>",
      "latest": "<date la plus récente>"
    },
    "iron_age_rows": "<nombre de lignes avec datation dans [-800, -25]>",
    "indeterminate_rows": "<nombre de lignes avec STARTING_PERIOD=Indéterminé>"
  },
  "quality": {
    "completeness": {
      "lat_lon_filled": "<% de lignes avec coordonnées>",
      "period_filled": "<% de lignes avec datation non-indéterminée>",
      "bibliography_filled": "<% de lignes avec BIBLIOGRAPHY non vide>"
    },
    "issues": [
      "description de chaque problème de qualité détecté"
    ],
    "confidence_level": "HIGH | MEDIUM | LOW"
  },
  "data_model": {
    "grain": "Un site peut avoir plusieurs lignes (une par caractéristique CARAC_*)",
    "primary_key_candidate": "SITE_SOURCE_ID (par base), SITE_AKG_ID (global ArkeoGIS)",
    "hierarchical_columns": ["CARAC_NAME", "CARAC_LVL1", "CARAC_LVL2", "CARAC_LVL3", "CARAC_LVL4"]
  }
}
```

**Méthode** : Charger le CSV avec pandas, calculer les statistiques, détecter les types, les valeurs nulles, les distributions.

### 3. `analysis.md` — Documentation et stratégie d'ingestion

Rédiger un document Markdown structuré couvrant :

#### 3.1 Vue d'ensemble
- Nom, origine, taille du jeu de données
- Contexte archéologique (âge du Fer, région, auteur)
- Format ArkeoGIS et spécificités

#### 3.2 Schéma détaillé des colonnes

Pour chaque colonne, documenter :
- Nom, type, description
- Taux de remplissage
- Valeurs distinctes (top 10 si catégoriel)
- Problèmes détectés (encodage, valeurs aberrantes, guillemets doubles malformés)

#### 3.3 Analyse du modèle de données

- **Grain** : Expliquer que dans ArkeoGIS, un même site (SITE_AKG_ID) peut apparaître sur plusieurs lignes, chacune décrivant une caractéristique différente (mobilier, immobilier, production). Documenter le ratio lignes/sites uniques.
- **Hiérarchie CARAC_***: Documenter l'arbre des caractéristiques (`CARAC_NAME` → `LVL1` → `LVL2` → `LVL3` → `LVL4`) avec les valeurs observées.
- **Datation ArkeoGIS** : Format `-YYYY:-YYYY` pour `STARTING_PERIOD` et `ENDING_PERIOD`. Expliquer comment le convertir en périodes BaseFerRhin (Hallstatt / La Tène / Transition) en utilisant `data/reference/periodes.json`.

#### 3.4 Analyse de qualité

- Valeurs manquantes par colonne (heatmap textuel)
- Valeurs aberrantes géographiques (coordonnées hors zone d'étude Rhin supérieur 47°–50°N / 7°–11°E)
- Doublons potentiels (même SITE_SOURCE_ID)
- Problèmes d'encodage (guillemets doubles doublés `""""`, caractères allemands)
- `CITY_CENTROID=Oui` → coordonnées au centroïde de la commune, pas du site exact → confiance spatiale réduite

#### 3.5 Mapping vers le modèle BaseFerRhin

Définir le mapping explicite vers les champs normalisés du projet :

| Champ ArkeoGIS | Champ BaseFerRhin | Transformation |
|---|---|---|
| `SITE_NAME` | `nom_site` | Nettoyage encodage |
| `MAIN_CITY_NAME` | `commune` | Normalisation via `data/reference/toponymes_fr_de.json` |
| `LONGITUDE` / `LATITUDE` | `longitude` / `latitude` | Vérification EPSG:4326 |
| `STARTING_PERIOD` / `ENDING_PERIOD` | `datation_debut` / `datation_fin` | Parsing format `-YYYY:-YYYY` |
| `CARAC_LVL1` | `type_site` | Mapping via `data/reference/types_sites.json` |
| `STATE_OF_KNOWLEDGE` | `etat_connaissance` | Vocabulaire contrôlé |
| `OCCUPATION` | `type_occupation` | Vocabulaire contrôlé |
| `BIBLIOGRAPHY` | `bibliographie` | Parsing multi-sources (séparateur `_`) |
| `COMMENTS` | `commentaires` | Texte libre, extraction mots-clés |
| `CARAC_EXP` | `exportation_attestee` | Booléen Oui/Non |

#### 3.6 Stratégie d'ingestion

Détailler les étapes :

1. **Chargement** : `pd.read_csv(path, sep=";", encoding="utf-8")`
2. **Nettoyage** :
   - Supprimer les guillemets doubles malformés
   - Normaliser les noms de communes (FR/DE via toponymes_fr_de.json)
   - Parser les datations `-YYYY:-YYYY` → `(int, int)`
3. **Dédoublonnage lignes → sites** :
   - Grouper par `SITE_AKG_ID` (ou `SITE_SOURCE_ID` + `DATABASE_NAME`)
   - Agréger les caractéristiques (CARAC_*) en liste
   - Fusionner la bibliographie
4. **Classification** :
   - Déterminer `type_site` via mapping `CARAC_LVL1` → `types_sites.json`
   - Déterminer `periode` via `periodes.json` et les dates
   - Évaluer `confiance` (HIGH si fouillé + coordonnées exactes, MEDIUM si sondé, LOW si centroïde)
5. **Géocodage** :
   - Valider les coordonnées dans la bounding box Rhin supérieur
   - Projeter en Lambert-93 (`pyproj`)
   - Marquer les centroïdes communaux (`CITY_CENTROID=Oui`)
6. **Export** : Produire des `RawRecord` compatibles avec le pipeline ETL existant

#### 3.7 Limites et précautions

- Biais de l'inventaire (couverture inégale selon les communes)
- Précision spatiale variable (centroïdes vs coordonnées de fouille)
- Datation souvent large ou indéterminée
- Données en allemand nécessitant une normalisation bilingue

### 4. `ingestion_prompt.md` — Prompt d'ingestion pour agent IA

Générer un prompt auto-contenu qu'un agent IA peut exécuter pour ingérer le fichier dans la base. Structure :

```markdown
# Prompt d'ingestion — <FILENAME>

## Contexte
- Projet : BaseFerRhin (inventaire âge du Fer du Rhin supérieur)
- Fichier source : `data/input/<FILENAME>.csv`
- Format : CSV ArkeoGIS (`;` séparateur, 22 colonnes)
- Volume : <N> lignes, <M> sites uniques

## Références obligatoires
- Schéma de types : `data/reference/types_sites.json`
- Périodes : `data/reference/periodes.json`
- Toponymes FR/DE : `data/reference/toponymes_fr_de.json`
- Golden sites (vérité terrain) : `data/sources/golden_sites.csv`
- Metadata : `data/analysis/<FILENAME>/metadata.json`

## Tâches

### T1 — Chargement et nettoyage
- Charger le CSV avec pandas (`sep=";"`, `encoding="utf-8"`)
- Nettoyer les guillemets doubles malformés (pattern `""""`)
- Normaliser les colonnes SITE_NAME et MAIN_CITY_NAME (strip, titre-case)
- Parser STARTING_PERIOD / ENDING_PERIOD → (int_debut, int_fin) via regex `-?\d+:-?\d+`
- Gérer les valeurs "Indéterminé" → None

### T2 — Agrégation sites
- Grouper par SITE_AKG_ID
- Pour chaque site, agréger :
  - Liste des CARAC_* (mobilier, immobilier, production)
  - Concaténation des BIBLIOGRAPHY (dédoublonnées)
  - Concaténation des COMMENTS
  - Période = union des STARTING_PERIOD / ENDING_PERIOD

### T3 — Classification
- Mapper CARAC_LVL1 → type_site normalisé via types_sites.json :
  - "Enceinte" → OPPIDUM
  - "Habitat" → HABITAT
  - "Funéraire" → NECROPOLE
  - "Dépôt" → DEPOT
  - "Forge" / "Métal" (sous Production) → ATELIER
  - Défaut → INDETERMINE
- Mapper dates → périodes via periodes.json
- Calculer confiance :
  - HIGH : STATE_OF_KNOWLEDGE in ["Fouillé"] AND CITY_CENTROID == "Non"
  - MEDIUM : STATE_OF_KNOWLEDGE in ["Sondé", "Littérature"]
  - LOW : CITY_CENTROID == "Oui" OR STATE_OF_KNOWLEDGE == "Non renseigné"

### T4 — Géocodage et projection
- Vérifier LONGITUDE ∈ [7.0, 11.0] et LATITUDE ∈ [47.0, 50.0]
- Projeter WGS84 → Lambert-93 (pyproj, EPSG:4326 → EPSG:2154)
- Marquer les coordonnées centroïdes

### T5 — Déduplication inter-sources
- Comparer avec les sites existants dans `data/output/sites.csv` et `data/sources/golden_sites.csv`
- Critères de correspondance :
  - Distance géographique < 500m ET même commune
  - OU même nom de site (fuzzy match > 0.85 via rapidfuzz)
- Marquer les doublons potentiels pour revue manuelle

### T6 — Export
- Produire un fichier `data/analysis/<FILENAME>/sites_cleaned.csv` avec le schéma normalisé :
  `site_id, nom_site, commune, pays, type_site, longitude, latitude, x_l93, y_l93, periode, sous_periode, datation_debut, datation_fin, confiance, source, bibliographie`
- Produire un fichier `data/analysis/<FILENAME>/quality_report.json` résumant les anomalies

## Validation
- Vérifier que le nombre de sites uniques correspond à l'attendu
- Vérifier qu'aucune coordonnée n'est hors bounding box
- Vérifier la cohérence des périodes (datation dans la plage de la période assignée)
- Cross-check avec golden_sites.csv (les sites connus doivent matcher)
```

---

## Analyse inter-fichiers (relations)

Après avoir analysé chaque fichier individuellement, produire un document de synthèse :

### Fichier : `data/analysis/CROSS_FILE_RELATIONS.md`

#### 1. Schéma commun

Les deux fichiers partagent le schéma ArkeoGIS (22 colonnes identiques). Documenter :
- Colonnes strictement identiques
- Différences de remplissage entre les fichiers
- Vocabulaire contrôlé partagé vs divergent

#### 2. Recouvrement géographique

- **LoupBernard** : Sites de l'âge du Fer du Bade-Wurtemberg entier (~110 sites, enceintes principalement)
- **ADAB2011** : Inventaire archéologique du Nordbaden, toutes périodes (~696 enregistrements)
- Zone de chevauchement : **Nord du Bade-Wurtemberg** (Nordbaden)
- Calculer le nombre de sites géographiquement proches (< 1 km) entre les deux fichiers
- Identifier les sites présents dans les deux fichiers (même MAIN_CITY_NAME + distance < 500m)

#### 3. Complémentarité chronologique

- **LoupBernard** : Exclusivement âge du Fer (Hallstatt / La Tène), datations précises
- **ADAB2011** : Toutes périodes, beaucoup de datations "Indéterminé"
- Les deux se complètent : LoupBernard apporte la précision chronologique, ADAB2011 le volume

#### 4. Complémentarité typologique

- **LoupBernard** : Dominé par les enceintes/oppida (CARAC_LVL1="Enceinte"), avec du mobilier détaillé (CARAC_LVL2-4)
- **ADAB2011** : Mix habitat, funéraire, production, voies, paysage
- Documenter la matrice de couverture typologique

#### 5. Relations avec les autres sources du projet

- `data/sources/golden_sites.csv` : Sites de référence (22 sites). Identifier les correspondances avec les fichiers input.
- `sub_projet/CAG Bas-Rhin/` : Notices de la Carte Archéologique de la Gaule 67/1. Recouvrement potentiel pour les sites alsaciens proches de la frontière.
- `data/raw/gallica/` : Sources Gallica (texte OCR). Pas de relation directe mais peut enrichir la bibliographie.

#### 6. Stratégie de fusion

Recommander l'ordre et la méthode de fusion :

1. **Ingérer LoupBernard en premier** (haute qualité, datations précises, sites de référence)
2. **Ingérer ADAB2011 ensuite** avec déduplication contre LoupBernard
3. **Cross-valider** avec golden_sites.csv
4. **Enrichir** avec les données CAG Bas-Rhin pour la zone frontalière

#### 7. Matrice de correspondance des champs

| Concept | LoupBernard | ADAB2011 | BaseFerRhin (cible) |
|---|---|---|---|
| ID site | SITE_SOURCE_ID | SITE_SOURCE_ID (BW_*) | site_id (généré) |
| Nom | SITE_NAME | SITE_NAME | nom_site |
| Commune | MAIN_CITY_NAME | MAIN_CITY_NAME | commune |
| Type | CARAC_LVL1 (Enceinte, Habitat...) | CARAC_LVL1 (Habitat, Funéraire...) | type_site (normalisé) |
| Période | STARTING/ENDING_PERIOD (-620:-531) | souvent "Indéterminé" | periode + sous_periode |
| Coordonnées | WGS84, souvent centroïde | WGS84, souvent centroïde | WGS84 + Lambert-93 |
| Biblio | Riche, sources primaires | Sèche, réf. AKTENZEICHEN | bibliographie (fusionnée) |
| Commentaires | Détaillés, en français/allemand | Structurés (LISTENTEXT, DAT_FEIN, TYP_FEIN...) | commentaires |
| Qualité spatiale | Centroïde communal fréquent | Précision variable (20m à 200m de tolérance) | confiance |

---

## Exécution

### Commande suggérée

```bash
cd /Users/I0438973/BaseFerRhin

# Créer les dossiers d'analyse
mkdir -p "data/analysis/20250806_LoupBernard_ArkeoGis"
mkdir -p "data/analysis/20250806_ADAB2011_ArkeoGis"

# Exécuter l'analyse (script Python ou agent IA)
python -c "
import pandas as pd
import json
from pathlib import Path

INPUT_DIR = Path('data/input')
ANALYSIS_DIR = Path('data/analysis')

for csv_path in sorted(INPUT_DIR.glob('*.csv')):
    name = csv_path.stem
    out_dir = ANALYSIS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, sep=';', encoding='utf-8')

    # Metadata
    meta = {
        'file_name': csv_path.name,
        'file_path': str(csv_path),
        'format': 'CSV',
        'separator': ';',
        'encoding': 'UTF-8',
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'columns': [
            {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'null_pct': round(df[col].isnull().mean() * 100, 1),
                'unique_count': int(df[col].nunique()),
                'sample_values': df[col].dropna().head(3).tolist()
            }
            for col in df.columns
        ],
        'source': {
            'platform': 'ArkeoGIS',
            'database_name': df['DATABASE_NAME'].iloc[0] if 'DATABASE_NAME' in df.columns else None,
        },
        'geographic': {
            'projection': 'EPSG:4326',
            'min_lat': float(df['LATITUDE'].min()) if 'LATITUDE' in df.columns else None,
            'max_lat': float(df['LATITUDE'].max()) if 'LATITUDE' in df.columns else None,
            'min_lon': float(df['LONGITUDE'].min()) if 'LONGITUDE' in df.columns else None,
            'max_lon': float(df['LONGITUDE'].max()) if 'LONGITUDE' in df.columns else None,
        }
    }
    (out_dir / 'metadata.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    # Sample
    df.head(20).to_csv(out_dir / 'sample_data.csv', sep=';', index=False)

    print(f'[OK] {name}: {len(df)} rows, {df.columns.tolist()}')
"
```

### Ce que l'agent doit produire au final

Pour chaque fichier dans `data/input/` :

| Livrable | Chemin | Contenu |
|---|---|---|
| Metadata JSON | `data/analysis/<NAME>/metadata.json` | Fiche technique complète |
| Documentation MD | `data/analysis/<NAME>/analysis.md` | Analyse, schéma, qualité, mapping, stratégie |
| Prompt d'ingestion | `data/analysis/<NAME>/ingestion_prompt.md` | Prompt exécutable par un agent |
| Sample data | `data/analysis/<NAME>/sample_data.csv` | 20 premières lignes |

Et un fichier de synthèse inter-fichiers :

| Livrable | Chemin | Contenu |
|---|---|---|
| Relations | `data/analysis/CROSS_FILE_RELATIONS.md` | Chevauchements, complémentarités, stratégie de fusion |
