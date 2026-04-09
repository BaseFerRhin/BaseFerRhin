## Context

Le projet BaseFerRhin possède un PDF de référence — la CAG 67/1 (735 pages, 209 Mo) — contenant l'inventaire archéologique complet du Bas-Rhin. Le scaffold du sous-projet `sub_projet/CAG Bas-Rhin/` existe déjà avec sa structure de répertoires, ses `__init__.py`, son `pyproject.toml` et son `config.yaml`. Le repo GitHub `BaseFerRhin/CAG-Bas-Rhin` est créé et contient le commit initial. Les fichiers Python sont des stubs vides qu'il faut implémenter.

Le PDF est en format natif (pas un scan) avec un layout 2 colonnes. `pdfplumber` peut extraire le texte mais mélange les colonnes si on ne crop pas. Les notices communales suivent un format structuré avec des patterns regex identifiables (NNN — NOM, N* (NNN), etc.).

Le projet parent BaseFerRhin utilise déjà Dash pour son UI et DuckDB n'est pas encore utilisé — c'est une opportunité de tester ce format léger.

## Goals / Non-Goals

**Goals:**

- Extraire de manière déterministe et idempotente les ~998 notices communales et ~3 000–5 000 sous-notices du PDF
- Filtrer les sous-notices pertinentes pour l'âge du Fer (~300–600 attendues)
- Persister les données structurées dans DuckDB avec un schéma relationnel normalisé
- Fournir une UI Dash interactive autonome pour explorer les données visuellement
- Permettre l'export vers le pipeline ETL parent BaseFerRhin
- Temps d'extraction < 2 minutes pour les 507 pages

**Non-Goals:**

- OCR ou traitement d'images/figures du PDF (hors scope)
- Extraction de la bibliographie générale (pages 7–79) — uniquement les refs inline des notices
- Géoréférencement précis des lieux-dits (seuls les centroïdes communaux sont géocodés)
- Intégration directe avec la base de données du projet parent (export JSON uniquement)
- Déploiement cloud ou conteneurisation de l'UI (usage local uniquement)

## Decisions

### D1 : pdfplumber avec crop demi-page pour les 2 colonnes

**Choix** : Cropper chaque page en deux moitiés (gauche `x0=0, x1=width/2`, droite `x0=width/2, x1=width`) puis concaténer.

**Alternatives considérées** :
- **PyMuPDF (fitz)** : plus rapide mais extraction texte moins fiable sur les layouts complexes
- **pdfplumber sans crop** : mélange les colonnes, texte inexploitable
- **Tabula** : orienté tables, pas adapté au texte libre

**Rationale** : pdfplumber est déjà dans les dépendances du scaffold, sa précision sur les colonnes croppées est prouvée par l'analyse préliminaire du PDF.

### D2 : DuckDB fichier local plutôt que SQLite ou PostgreSQL

**Choix** : DuckDB en mode fichier local (`data/cag67.duckdb`).

**Alternatives considérées** :
- **SQLite** : bien supporté mais pas de types analytiques natifs (pas de `FILTER WHERE`, pas de colonnes `LIST`)
- **PostgreSQL** : overkill pour un projet autonome mono-utilisateur
- **Parquet** : pas de schéma relationnel avec FK, pas de vues

**Rationale** : DuckDB offre SQL analytique riche (FILTER, LIST_AGG, window functions), zéro config serveur, fichier unique portable, et support Python natif via `duckdb.connect()`. Note : DuckDB supporte aussi une extension FTS (full-text search via `PRAGMA create_fts_index`) qui pourra être activée si la recherche textuelle LIKE s'avère trop lente sur le corpus. Important : DuckDB n'a pas de syntaxe `INSERT OR REPLACE` — l'upsert se fait via `INSERT ... ON CONFLICT DO UPDATE` ou un pattern transactionnel DELETE/INSERT.

### D3 : Dash multi-pages avec thème DARKLY

**Choix** : Dash Pages + dash-bootstrap-components thème DARKLY sur port 8051.

**Alternatives considérées** :
- **Streamlit** : plus simple mais moins de contrôle sur le layout et les callbacks croisés
- **Panel/Bokeh** : écosystème moins mature pour les cartes
- **React standalone** : trop lourd pour un projet archéologique de recherche

**Rationale** : cohérence avec le projet parent BaseFerRhin (Dash), richesse des composants Plotly (Scattermapbox, Sunburst, Timeline), support natif du multi-pages.

### D4 : Click CLI plutôt qu'argparse

**Choix** : CLI basé sur Click avec sous-commandes `extract`, `geocode`, `export`, `stats`.

**Rationale** : Click offre une meilleure ergonomie (décorateurs, aide auto-générée, types validés) et est déjà dans le scaffold `pyproject.toml`.

### D5 : API BAN pour le géocodage des communes

**Choix** : API BAN (Base Adresse Nationale) via httpx pour obtenir les centroïdes communaux.

**Alternatives considérées** :
- **Fichier INSEE pré-compilé** : précis mais nécessite un fichier externe à maintenir
- **Nominatim/OSM** : rate-limited et moins précis pour les communes françaises
- **Fichier GeoJSON communes** : statique, ne suit pas les fusions de communes

**Rationale** : BAN est officiel, gratuit, sans clé API, et retourne directement les coordonnées WGS84. Throttling à 1 req/100ms pour rester courtois.

### D6 : Architecture en 4 phases séquentielles

**Choix** : Pipeline linéaire `PDF → PageText → CommuneNotice → SubNotice → SiteRecord`.

**Rationale** : chaque phase a une responsabilité unique, est testable isolément, et produit un type intermédiaire clair. Pas besoin de parallélisme (l'extraction est I/O-bound sur le PDF, ~90s total).

## Risks / Trade-offs

- **[Qualité extraction colonnes]** Le crop à width/2 peut échouer sur certaines pages avec des figures pleine largeur ou des tableaux → Mitigation : détecter les pages avec tables via `page.extract_tables()` et fallback sur extraction pleine page
- **[Regex notices]** Les patterns `NNN — Nom` et `N* (NNN)` peuvent avoir des variantes non prévues → Mitigation : logging `WARNING` pour les pages sans match, compteur de couverture en fin d'extraction, revue manuelle des pages orphelines
- **[Volume sous-notices]** L'estimation 300–600 notices Fer est basée sur un échantillon — le volume réel peut varier → Mitigation : pas de hard-limit, les vues DuckDB s'adaptent dynamiquement
- **[API BAN disponibilité]** Le géocodage dépend d'un service externe → Mitigation : cache local des résultats dans `communes_geo.json`, mode offline si le fichier existe
- **[Taille PDF en mémoire]** 209 Mo en PDF, pdfplumber charge page par page donc ~5 Mo max en RAM → Risque faible
- **[Communes multi-pages]** Strasbourg (~50 pages) crée des notices très longues → Mitigation : concaténation progressive avec buffer par commune_id, pas de limite de taille
- **[Normalisation des périodes]** Les mentions chronologiques dans le PDF sont très variantes ("Ha D1", "Ha. D1", "Hallstatt D", "période de Hallstatt final") → Mitigation : un mapping de normalisation `periode_raw → periode_norm` (vocabulaire contrôlé : Ha A, Ha B, Ha C, Ha D1, Ha D2, Ha D3, LT A, LT B, LT C, LT D) est stocké en colonne `periode_norm` dans la table `periodes`. Les vues et charts utilisent `periode_norm` pour des statistiques fiables.
- **[Termes germaniques]** Le Bas-Rhin a une tradition archéologique bilingue FR/DE (Forrer, Hatt, etc.) → Mitigation : les regex d'extraction incluent des termes allemands (Grabhügel, Ringwall, Siedlung, Brandgrab, Viereckschanze, Fürstengrab)
