# CAG Bas-Rhin — Sous-projet autonome d'extraction et visualisation

## Vue d'ensemble

Sous-projet standalone pour l'extraction, le stockage et la visualisation interactive des données archéologiques de la **Carte Archéologique de la Gaule 67/1 — Le Bas-Rhin** (PDF natif, 735 pages, 209 Mo).

```
Repo GitHub : https://github.com/BaseFerRhin/CAG-Bas-Rhin
Emplacement : sub_projet/CAG Bas-Rhin/
Stack       : Python 3.11+ · pdfplumber · DuckDB · Dash · Plotly
```

Le projet est **autonome** (son propre `pyproject.toml`, ses propres tests) mais produit aussi des données compatibles avec le pipeline ETL parent BaseFerRhin.

---

## Fichier source

```
RawData/GrosFichiers - Béhague/CAG Bas-Rhin.pdf
  Format    : PDF/X-3:2002 (Adobe InDesign CS6)
  Pages     : 735
  Taille    : 209 Mo
  Créé      : 2016-07-06
  Auteurs   : Pascal Flotté, Matthieu Fuchs
  Communes  : 998 (numéros 001–999)
  Dept      : Bas-Rhin (67)
```

## Structure du PDF (analyse complète)

| Section | Pages | Contenu |
|---|---|---|
| Couverture + crédits | 1–6 | Titre, auteurs, avant-propos, préface |
| Bibliographie | 7–79 | Références bibliographiques (~73 pages) |
| Introduction | 80–153 | Cadre géographique, géologique, chronologique |
| **Notices communales** | **154–660** | **507 pages — ~998 communes (001–999)** |
| Index alphabétique | 661–735 | Index des vestiges, types, communes, figures |

### Statistiques âge du Fer dans les notices

| Terme | Occurrences | Pages touchées |
|---|---|---|
| Hallstatt | 645 | 380 / 507 pages |
| La Tène | 376 | — |
| tumulus | 382 | — |
| nécropole | 264 | — |
| âge du Fer | 75 | — |
| protohistorique | 64 | — |
| oppidum | 29 | — |
| Figures (Fig. NNN) | 1 349 | — |
| Tables inline | 15 | — |

### Structure d'une notice communale

```
NNN — NOM-COMMUNE (superficie ; alt. entre X m et Y m)
La commune se situe dans [contexte géo]. Sa première mention connue est [...]

1* (001) Au lieu-dit Xxxxxx, [description de la découverte]...
   [datation, mobilier, bibliographie]
2* (002) Description d'un autre site ou secteur...
N* (NNN XX) Au lieu-dit Yyyyy, ... [sous-notice avec code lieu-dit]
```

**Patterns observés :**
- En-tête commune : `Commune NNN` ou `Communes NNN à NNN` dans le header de page
- Code commune : `NNN — Nom-Commune` (3 chiffres, tiret cadratin)
- Sous-notices numérotées : `N* (NNN)` où N est le numéro séquentiel et NNN un code spatial
- Sous-notices avec lieu-dit : `(NNN XX)` ou `(NNN XX, NNN YY)` — code + lettres majuscules
- Bibliographie inline : `Auteur, 1999` / `Gallia, 1978, p. 370`
- PDF natif (pas un scan) — `pdfplumber` extrait du texte exploitable
- Mise en page **2 colonnes** → `pdfplumber` mélange parfois les colonnes
- Légendes de figures intercalées dans le texte

---

## Architecture du sous-projet

### Arbre des fichiers

```
sub_projet/CAG Bas-Rhin/
├── README.md
├── pyproject.toml
├── requirements.txt
├── config.yaml                      # Config extraction (page_range, seuils)
│
├── src/
│   ├── __init__.py
│   ├── __main__.py                  # CLI: python -m src (extract + load)
│   │
│   ├── extraction/                  # Phase 1-4 : PDF → notices → records
│   │   ├── __init__.py
│   │   ├── pdf_reader.py            # Phase 1 : pdfplumber page extraction
│   │   ├── commune_splitter.py      # Phase 2 : split en notices communales
│   │   ├── notice_parser.py         # Phase 3 : split sous-notices + lieu-dits
│   │   ├── iron_age_filter.py       # Phase 4 : filtre âge du Fer
│   │   ├── record_builder.py        # Phase 4 : construction SiteRecord
│   │   └── pipeline.py              # Orchestrateur des 4 phases
│   │
│   ├── storage/                     # DuckDB persistence
│   │   ├── __init__.py
│   │   ├── schema.py                # Création tables/vues DuckDB
│   │   ├── loader.py                # Insert records → DuckDB
│   │   └── queries.py               # Requêtes analytiques pré-définies
│   │
│   ├── export/                      # Export vers pipeline parent
│   │   ├── __init__.py
│   │   └── to_raw_records.py        # Conversion → RawRecord BaseFerRhin
│   │
│   └── ui/                          # Interface Dash interactive
│       ├── __init__.py
│       ├── __main__.py              # python -m src.ui → http://localhost:8051
│       ├── app.py                   # Factory Dash
│       ├── layout.py                # Layout principal
│       ├── callbacks.py             # Callbacks interactifs
│       ├── pages/
│       │   ├── __init__.py
│       │   ├── carte.py             # Page carte : communes avec sites Fer
│       │   ├── notices.py           # Page navigateur : lecture notices PDF
│       │   ├── stats.py             # Page statistiques : dashboards
│       │   └── chronologie.py       # Page frise : timeline Hallstatt / La Tène
│       ├── components/
│       │   ├── __init__.py
│       │   ├── notice_card.py       # Carte de notice (texte, metadata)
│       │   ├── commune_map.py       # Carte Plotly Scattermapbox
│       │   ├── period_chart.py      # Bar chart périodes
│       │   └── type_chart.py        # Donut chart types de sites
│       └── assets/
│           └── cag.css              # Thème sombre archéologique
│
├── tests/
│   ├── __init__.py
│   ├── test_pdf_reader.py
│   ├── test_commune_splitter.py
│   ├── test_notice_parser.py
│   ├── test_iron_age_filter.py
│   ├── test_record_builder.py
│   ├── test_duckdb_storage.py
│   └── fixtures/
│       └── sample_pages.json        # Texte extrait de 10 pages de test
│
├── data/
│   ├── cag67.duckdb                 # Base DuckDB générée
│   └── communes_geo.json            # Centroïdes communes Bas-Rhin (GeoJSON)
│
└── .gitignore
```

### Principes Clean Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Présentation                           │
│                  src/ui/ (Dash multi-pages)                 │
├────────────────────────────────────────────────────────────┤
│                    Application                             │
│        src/extraction/pipeline.py (orchestration)          │
├────────────────────────────────────────────────────────────┤
│                      Domaine                               │
│   Models (SiteRecord, CommuneNotice, SubNotice)            │
│   Filtres (iron_age_filter), Classification (guess_type)   │
├────────────────────────────────────────────────────────────┤
│                   Infrastructure                           │
│   pdfplumber (PDF read), DuckDB (storage), geocoding       │
└────────────────────────────────────────────────────────────┘
```

---

## Phase 1 : Extraction PDF (`pdf_reader.py`)

```python
class PDFReader:
    """Extract text from CAG 67/1 PDF page by page."""
    
    def __init__(self, pdf_path: Path, page_range: tuple[int, int] = (154, 660)):
        ...
    
    def read_pages(self) -> list[PageText]:
        """Extract text from each page in range, handling 2-column layout."""
        ...
```

- Utiliser `pdfplumber.open()` avec extraction page par page
- **Limiter aux pages 154–660** (notices communales uniquement)
- Stratégie colonnes : `page.crop()` pour extraire colonne gauche puis droite séparément
  - Colonne gauche : `x0=0, x1=width/2`
  - Colonne droite : `x0=width/2, x1=width`
  - Concaténer gauche + droite pour chaque page
- Détecter la commune courante via le header `Commune NNN` ou `Communes NNN à NNN`
- Capturer les tables inline via `page.extract_tables()`
- Retourner `list[PageText]` avec `(page_num, text, commune_header, tables)`

## Phase 2 : Découpage communal (`commune_splitter.py`)

```python
class CommuneSplitter:
    """Split aggregated text into individual commune notices."""
    
    def split(self, pages: list[PageText]) -> list[CommuneNotice]:
        """Aggregate pages by commune, then split by pattern."""
        ...
```

Pattern commune adapté au format PDF :

```python
_COMMUNE_PDF_RE = re.compile(
    r"^(\d{3})\s*[-–—]\s*([A-ZÀ-Ü][a-zà-ÿA-ZÀ-Ü\-\s']+)"
    r"(?:\s*\([\d\s]+ha\s*;[^)]+\))?",
    re.MULTILINE
)
```

- Concaténer les textes de pages consécutives d'une même commune (détection par header)
- Gérer les communes multi-pages (Brumath ~10p, Strasbourg ~50p)
- **Attente : ~998 notices communales**

## Phase 3 : Parsing sous-notices (`notice_parser.py`)

```python
class NoticeParser:
    """Parse a commune notice into sub-notices (lieu-dit level)."""
    
    def parse(self, notice: CommuneNotice) -> list[SubNotice]:
        """Split by N* (NNN) or (NNN XX) patterns."""
        ...
```

Deux patterns de sous-notices :

```python
# Pattern 1 : numérotées "N* (NNN)" ou "N* (NNN XX)"
_NUMBERED_RE = re.compile(r"\n\s*(\d+)\*\s*\((\d{3}(?:\s*[A-Z]{2})?)\)\s*")

# Pattern 2 : code lieu-dit seul "(NNN XX)" sans numéro d'astérisque
_LIEU_DIT_CODE_RE = re.compile(r"\n\s*\((\d{3}\s*[A-Z]{2}(?:,\s*\d{3}\s*[A-Z]{2})*)\)\s*")
```

Extraire pour chaque sous-notice :
- `lieu_dit` : texte après "Au(x) lieu(x)-dit(s)" ou nom de lieu
- `sous_notice_code` : code spatial (ex: `007`, `003 AH`)
- `texte` : corps de la sous-notice
- `bibliographie` : références inline (`Auteur, 1999`)
- `figures_refs` : `Fig. 28`, `Fig. 30b`

## Phase 4 : Filtrage et construction (`iron_age_filter.py` + `record_builder.py`)

### Filtre âge du Fer

```python
_FER_KEYWORDS = re.compile(
    r"(?i)\b(?:hallstatt|la\s+tène|âge\s+du\s+fer|protohistor|"
    r"tumulus|tertre\s+funéraire|Ha\s*[CD]\d?|LT\s*[A-D]\d?|"
    r"premier\s+âge\s+du\s+fer|second\s+âge\s+du\s+fer|"
    r"âge\s+du\s+bronze\s+final|BF\s*III|"
    r"époque\s+de\s+hallstatt|eisenzeit|latènezeit)\b"
)
```

**Règle** : retenir si au moins un match `_FER_KEYWORDS`. Exclure les notices purement gallo-romaines, mérovingiennes, néolithiques ou médiévales.

### Classification des vestiges

```python
_VESTIGES_KEYWORDS = re.compile(
    r"(?i)\b(?:tumulus|tertre|sépulture|nécropole|habitat|oppidum|"
    r"fortification|enceinte|silo|fosse|four|atelier|dépôt|"
    r"tombe|inhumation|incinération|urne|céramique|tessons?|"
    r"fibule|bracelet|épée|monnaie|torque|hache|rasoir|"
    r"poignard|anneau|poterie|urn|brandgrab)\b"
)
```

### Modèle `SiteRecord`

```python
@dataclass
class SiteRecord:
    commune_id: str                    # "001", "067"
    commune_name: str                  # "Achenheim"
    sous_notice_code: str | None       # "007", "003 AH"
    lieu_dit: str | None               # "Todtenallee"
    type_site: str                     # nécropole, habitat, oppidum, etc.
    periode_mentions: list[str]        # ["Hallstatt", "La Tène"]
    vestiges_mentions: list[str]       # ["tumulus", "fibule"]
    raw_text: str                      # Texte de la sous-notice (tronqué 500 chars)
    full_text: str                     # Texte complet (stocké en DuckDB)
    page_number: int                   # Page PDF source
    bibliographie: list[str]           # Refs biblio
    figures_refs: list[str]            # "Fig. 28", "Fig. 30b"
    has_iron_age: bool                 # True si filtre Fer passé
    all_periods: list[str]             # Toutes les mentions chrono (y compris non-Fer)
```

### Volumes attendus

| Métrique | Estimation |
|---|---|
| Pages traitées | 507 (p.154–660) |
| Notices communales | ~998 |
| Sous-notices totales | ~3 000–5 000 (toutes périodes) |
| **Sous-notices âge du Fer** | **~300–600** |
| Temps d'extraction | ~60–90s |

---

## Base de données DuckDB (`storage/`)

### Schéma (`schema.py`)

```sql
CREATE TABLE IF NOT EXISTS communes (
    commune_id    VARCHAR PRIMARY KEY,   -- '001'
    commune_name  VARCHAR NOT NULL,
    page_start    INTEGER,
    page_end      INTEGER,
    latitude      DOUBLE,                -- Centroïde WGS84
    longitude     DOUBLE,
    x_l93         DOUBLE,                -- Lambert-93
    y_l93         DOUBLE
);

CREATE TABLE IF NOT EXISTS notices (
    notice_id         VARCHAR PRIMARY KEY,  -- 'CAG67-001-007'
    commune_id        VARCHAR NOT NULL REFERENCES communes(commune_id),
    sous_notice_code  VARCHAR,              -- '007', '003 AH'
    lieu_dit          VARCHAR,
    type_site         VARCHAR,              -- oppidum, habitat, nécropole...
    raw_text          VARCHAR,              -- Tronqué 500 chars
    full_text         VARCHAR,              -- Texte complet
    page_number       INTEGER,
    has_iron_age      BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS periodes (
    notice_id     VARCHAR NOT NULL REFERENCES notices(notice_id),
    periode       VARCHAR NOT NULL,          -- 'Hallstatt', 'La Tène', 'gallo-romain'...
    is_iron_age   BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS vestiges (
    notice_id     VARCHAR NOT NULL REFERENCES notices(notice_id),
    vestige       VARCHAR NOT NULL            -- 'tumulus', 'fibule', 'céramique'...
);

CREATE TABLE IF NOT EXISTS bibliographie (
    notice_id     VARCHAR NOT NULL REFERENCES notices(notice_id),
    reference     VARCHAR NOT NULL            -- 'Forrer, 1923a'
);

CREATE TABLE IF NOT EXISTS figures (
    notice_id     VARCHAR NOT NULL REFERENCES notices(notice_id),
    figure_ref    VARCHAR NOT NULL,           -- 'Fig. 28'
    page_number   INTEGER
);

-- Vues analytiques
CREATE VIEW IF NOT EXISTS v_fer_notices AS
SELECT n.*, c.commune_name, c.latitude, c.longitude
FROM notices n JOIN communes c ON n.commune_id = c.commune_id
WHERE n.has_iron_age = true;

CREATE VIEW IF NOT EXISTS v_stats_by_commune AS
SELECT c.commune_id, c.commune_name, c.latitude, c.longitude,
       COUNT(*) as total_notices,
       COUNT(*) FILTER (WHERE n.has_iron_age) as fer_notices,
       COUNT(DISTINCT n.type_site) as type_count
FROM communes c LEFT JOIN notices n ON c.commune_id = n.commune_id
GROUP BY c.commune_id, c.commune_name, c.latitude, c.longitude;

CREATE VIEW IF NOT EXISTS v_stats_by_type AS
SELECT type_site, COUNT(*) as count,
       COUNT(*) FILTER (WHERE has_iron_age) as fer_count
FROM notices GROUP BY type_site ORDER BY count DESC;

CREATE VIEW IF NOT EXISTS v_stats_by_periode AS
SELECT p.periode, p.is_iron_age, COUNT(DISTINCT p.notice_id) as notice_count
FROM periodes p GROUP BY p.periode, p.is_iron_age ORDER BY notice_count DESC;
```

### Centroïdes communes (`communes_geo.json`)

Générer un fichier GeoJSON avec les centroïdes de toutes les communes du Bas-Rhin via l'API BAN :

```bash
python -m src --geocode-communes
```

Cela peuple la table `communes` avec `latitude`, `longitude`, `x_l93`, `y_l93` pour chaque commune trouvée dans le PDF.

---

## Interface web Dash (`src/ui/`)

### Stack

- **Dash** >= 2.14 + **dash-bootstrap-components** >= 1.5 (thème DARKLY)
- **Dash Pages** (multi-pages routing)
- **Plotly** Scattermapbox + Bar + Sunburst + Timeline
- **DuckDB** direct (queries SQL depuis les callbacks)
- Police **Inter** (Google Fonts)
- Port : **8051** (distinct du BaseFerRhin parent sur 8050)

### Lancement

```bash
cd "sub_projet/CAG Bas-Rhin"
python -m src.ui
# → http://localhost:8051
```

### Pages et layout

```
┌────────────────────────────────────────────────────────────────┐
│  CAG 67/1 — Carte Archéologique du Bas-Rhin                   │
│  [Carte]  [Notices]  [Chronologie]  [Statistiques]             │
├────────────────────────────────────────────────────────────────┤
│                     (contenu de page)                          │
└────────────────────────────────────────────────────────────────┘
```

#### Page 1 : Carte (`pages/carte.py`)

```
┌─────────────────────────────────────────────────────────────┐
│                    CARTE INTERACTIVE                         │
│              (Plotly Scattermapbox, OSM tiles)               │
│                                                             │
│   ● Achenheim (3 notices Fer)                               │
│       ● Brumath (15 notices Fer)                            │
│                  ● Strasbourg (25 notices Fer)              │
│                                                             │
│   Centre: 48.6°N, 7.75°E   Zoom: 9                         │
│   Coloration: nombre de notices Fer (gradient)              │
├──────────────┬──────────────────────────────────────────────┤
│ FILTRES      │  DÉTAIL COMMUNE (clic carte)                 │
│ Type site    │  Commune 002 — Achenheim                     │
│ Période      │  6* (007) Lœssière — rasoir La Tène finale   │
│ Nb notices   │  7* (008) Village — restes romains            │
│              │  [Voir notice complète →]                     │
└──────────────┴──────────────────────────────────────────────┘
```

- Points = communes (centroïdes géocodés)
- Taille = nombre de sous-notices âge du Fer
- Couleur = type dominant (nécropole, habitat, oppidum...) ou gradient densité
- Hover : commune, nb notices, types
- Clic : affiche les sous-notices dans le panneau latéral

#### Page 2 : Navigateur de notices (`pages/notices.py`)

```
┌──────────────┬──────────────────────────────────────────────┐
│ COMMUNES     │  NOTICE DÉTAILLÉE                            │
│              │                                              │
│ 🔍 Recherche │  002 — Achenheim                             │
│              │  (1 360 ha ; alt. entre 150 m et 270 m)      │
│ □ Fer seul   │                                              │
│              │  6* (007) Dans une lœssière (sans             │
│ 001 Achenhe… │  précision), un rasoir à manche recourbé     │
│ 002 Achenhe… │  de La Tène finale a été découvert dans      │
│ 005 Altecken │  une sépulture à incinération...             │
│ 007 Altorf   │                                              │
│ 008 Altorf   │  Bibliographie:                              │
│ ...          │  R. Forrer 1923a, p. 106                     │
│              │  B. Normand, 1973, p. 77                     │
│              │                                              │
│ Total: 998   │  Tags: [La Tène] [rasoir] [sépulture]        │
│ Fer: ~300    │  Page PDF: 155                                │
└──────────────┴──────────────────────────────────────────────┘
```

- Liste scrollable des communes (filtrables par texte, type, période)
- Toggle "Fer uniquement" pour ne voir que les notices âge du Fer
- Panneau droit : texte complet de la notice avec highlights des mots-clés
- Tags cliquables (période, vestiges) pour cross-filter
- Lien vers la page PDF source

#### Page 3 : Chronologie (`pages/chronologie.py`)

```
┌─────────────────────────────────────────────────────────────┐
│                 FRISE CHRONOLOGIQUE                          │
│                                                             │
│  Néolithique ████                                           │
│  Bronze      █████████                                      │
│  Hallstatt   ██████████████████  (645 mentions)             │
│  La Tène     ████████████████    (376 mentions)             │
│  Gallo-rom.  ██████████████████████████████████              │
│  Mérovingien ████████████                                   │
│  Médiéval    ████████                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  SOUS-PÉRIODES FER                                          │
│  Ha C ██   Ha D1 ████   Ha D2 ██   Ha D3 █████             │
│  LT A ████   LT B ███   LT C █████   LT D ████            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  CO-OCCURRENCES CHRONOLOGIQUES                              │
│  (Heatmap : quelles périodes apparaissent ensemble)         │
└─────────────────────────────────────────────────────────────┘
```

- Vue panoramique de toutes les périodes mentionnées (pas uniquement Fer)
- Zoom sur les sous-périodes de l'âge du Fer
- Heatmap de co-occurrences (Hallstatt + La Tène, Bronze + Hallstatt...)
- Données directement depuis DuckDB (`v_stats_by_periode`)

#### Page 4 : Statistiques (`pages/stats.py`)

```
┌───────────────────┬─────────────────┬───────────────────────┐
│  SYNTHÈSE         │  PAR TYPE       │  PAR COMMUNE          │
│                   │                 │                       │
│  998 communes     │  🍩 Donut       │  Top 20 communes      │
│  ~4000 notices    │  nécropole 40%  │  (bar chart)          │
│  ~400 Fer         │  habitat   25%  │                       │
│  ~600 gallo-rom.  │  oppidum   8%   │  Strasbourg: 25       │
│                   │  tumulus   15%  │  Brumath: 15          │
│  1349 figures     │  dépôt     5%   │  Haguenau: 12         │
│  15 tables        │  autre     7%   │  ...                  │
├───────────────────┴─────────────────┴───────────────────────┤
│  NUAGE DE VESTIGES (word cloud ou treemap)                  │
│  tumulus ████  fibule ██  céramique ████  sépulture ███     │
│  bracelet ██  épée █  monnaie ██  tessons ███               │
└─────────────────────────────────────────────────────────────┘
```

- KPI cards (totaux, Fer, gallo-romain...)
- Donut chart types de sites
- Bar chart top communes
- Treemap ou word cloud des vestiges les plus fréquents
- Sunburst : période → type → commune

### Thème CSS (`assets/cag.css`)

Thème sombre archéologique cohérent avec le projet parent :
- Background : `#0f0f1a`
- Surface : `#16182d`
- Accent Hallstatt : `#D95F02` (orange)
- Accent La Tène : `#1B9E77` (vert)
- Accent gallo-romain : `#7570B3` (violet)
- Police : Inter

### Palettes de couleurs

| Type site | Hex |
|---|---|
| oppidum | `#E31A1C` |
| habitat | `#1F78B4` |
| nécropole | `#6A3D9A` |
| dépôt | `#FF7F00` |
| sanctuaire | `#33A02C` |
| atelier | `#B15928` |
| tumulus | `#FB9A99` |
| indéterminé | `#B2DF8A` |

---

## Export vers pipeline parent

### Conversion DuckDB → RawRecords (`export/to_raw_records.py`)

```python
def export_to_raw_records(db_path: Path) -> list[dict]:
    """Export Iron Age notices from DuckDB as RawRecord-compatible dicts.
    
    Produces dicts compatible with BaseFerRhin's RawRecord dataclass,
    ready to be injected into the parent pipeline via config.yaml.
    """
```

### Intégration pipeline parent (`config.yaml` BaseFerRhin)

```yaml
sources:
  # ... sources existantes ...
  - path: "sub_projet/CAG Bas-Rhin/data/cag67.duckdb"
    type: cag_duckdb
    options:
      source_label: cag_67
      iron_age_only: true
```

---

## CLI et workflow

### Commandes principales

```bash
cd "sub_projet/CAG Bas-Rhin"

# Extraction complète : PDF → DuckDB
python -m src extract --pdf "../../RawData/GrosFichiers - Béhague/CAG Bas-Rhin.pdf"

# Géocodage des communes (centroïdes BAN)
python -m src geocode

# Lancer l'UI
python -m src.ui
# → http://localhost:8051

# Export pour pipeline parent
python -m src export --format raw-records --output ../../data/sources/cag67_records.json

# Stats rapides
python -m src stats
```

### Workflow complet

```bash
# 1. Installation
cd "sub_projet/CAG Bas-Rhin"
pip install -e ".[dev]"

# 2. Extraction (PDF 209 Mo → DuckDB, ~90s)
python -m src extract --pdf "../../RawData/GrosFichiers - Béhague/CAG Bas-Rhin.pdf"
# → data/cag67.duckdb créée

# 3. Géocodage communes (API BAN, ~30s pour 998 communes)
python -m src geocode
# → Table communes mise à jour avec lat/lon

# 4. Visualisation
python -m src.ui

# 5. (Optionnel) Export vers pipeline parent
python -m src export --format raw-records --output ../../data/sources/cag67_records.json
cd ../..
python -m src --config config.yaml --start-from INGEST
```

---

## Tests

```bash
cd "sub_projet/CAG Bas-Rhin"
pytest                    # Tous les tests
pytest -k "pdf_reader"    # Un module
```

| Module | Couverture |
|---|---|
| `test_pdf_reader.py` | Extraction texte, 2 colonnes, tables, page range |
| `test_commune_splitter.py` | Split communes, multi-pages, edge cases |
| `test_notice_parser.py` | Sous-notices N*, (NNN XX), lieu-dits |
| `test_iron_age_filter.py` | Filtre Fer, exclusion gallo-romain, edge cases |
| `test_record_builder.py` | Construction SiteRecord, guess_type, bibliographie |
| `test_duckdb_storage.py` | Schéma, insert, vues analytiques, queries |

Fixture : `tests/fixtures/sample_pages.json` contient le texte extrait de 10 pages représentatives (p.155, 200, 300, 350, 401, 500, 550, 600, 650, 660).

---

## Dépendances (`pyproject.toml`)

```toml
[project]
name = "cag-bas-rhin"
version = "0.1.0"
description = "Extraction et visualisation de la Carte Archéologique de la Gaule 67/1 (Bas-Rhin)"
requires-python = ">=3.11"
dependencies = [
    "pdfplumber>=0.11",
    "duckdb>=1.1",
    "pyproj>=3.6",
    "httpx>=0.27",
    "pyyaml>=6.0",
    "rich>=13.0",
    "click>=8.0",
]

[project.optional-dependencies]
ui = [
    "dash>=2.14",
    "dash-bootstrap-components>=1.5",
    "dash-extensions>=1.0",
]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
]

[project.scripts]
cag67 = "src.__main__:cli"
```

---

## Résumé des livrables

| Fichier | Action |
|---|---|
| `sub_projet/CAG Bas-Rhin/` | CRÉER — projet autonome complet |
| `src/extraction/*.py` | CRÉER — 6 modules d'extraction PDF |
| `src/storage/*.py` | CRÉER — 3 modules DuckDB |
| `src/export/to_raw_records.py` | CRÉER — export pipeline parent |
| `src/ui/**/*.py` | CRÉER — ~12 modules Dash (4 pages, 4 composants, layout) |
| `tests/test_*.py` | CRÉER — 6 modules de tests |
| `README.md` | CRÉER — doc complète |
| `pyproject.toml` | CRÉER — config projet |
| `config.yaml` | CRÉER — config extraction |

## Contraintes qualité

- Chaque module < 200 lignes (split si nécessaire)
- Early return pattern systématique
- Pas de `utils.py` ou `helpers.py` — noms de modules domain-specific
- Queries DuckDB dans `queries.py` uniquement (pas dans les callbacks)
- UI responsive : fonctionne sur écrans 1280px+
- Extraction déterministe et idempotente
- Logging : `INFO` pour les totaux, `DEBUG` pour chaque commune
- Temps d'extraction cible : < 2 minutes pour les 507 pages
- Git : `data/cag67.duckdb` dans `.gitignore` (régénérable)
