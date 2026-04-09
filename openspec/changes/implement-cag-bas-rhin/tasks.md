## 1. Modèles de domaine et configuration

- [x] 1.1 Créer les dataclasses `PageText`, `CommuneNotice`, `SubNotice`, `SiteRecord` (avec champ `confidence_level`) dans `src/extraction/__init__.py` (ou un `models.py` dédié)
- [x] 1.2 Valider et compléter `config.yaml` avec tous les paramètres : pdf_path, page_range, db_path, geocoding throttle, UI port
- [x] 1.3 Créer un module `src/config.py` pour charger et valider la config YAML avec des valeurs par défaut

## 2. Extraction PDF (Phase 1)

- [x] 2.1 Implémenter `PDFReader` dans `src/extraction/pdf_reader.py` : ouverture PDF, crop gauche/droite, extraction texte page par page, détection header commune
- [x] 2.2 Gérer le fallback full-page pour les pages avec figures pleine largeur (détection via `extract_tables()`)
- [x] 2.3 Implémenter `page.extract_tables()` pour capturer les tables inline

## 3. Découpage communal (Phase 2)

- [x] 3.1 Implémenter `CommuneSplitter.split()` dans `src/extraction/commune_splitter.py` : regex `^\d{3}\s*[-–—]\s*[A-ZÀ-Ü]`, concaténation multi-pages
- [x] 3.2 Gérer les pages sans header (continuation) en les rattachant à la commune précédente
- [x] 3.3 Ajouter le logging INFO pour le nombre total de communes détectées et WARNING pour les pages orphelines

## 4. Parsing sous-notices (Phase 3)

- [x] 4.1 Implémenter `NoticeParser.parse()` dans `src/extraction/notice_parser.py` : patterns `N* (NNN)` et `(NNN XX)`
- [x] 4.2 Extraire `lieu_dit` via pattern "Au(x) lieu(x)-dit(s)" ou nom de lieu après le code
- [x] 4.3 Extraire les références bibliographiques inline (pattern `Auteur, AAAA`)
- [x] 4.4 Extraire les références de figures (pattern `Fig. NNN[a-z]?`)
- [x] 4.5 Gérer le cas des communes sans sous-notices (texte unique)

## 5. Filtrage âge du Fer et construction records (Phase 4)

- [x] 5.1 Implémenter `is_iron_age()` dans `src/extraction/iron_age_filter.py` avec le regex `_FER_KEYWORDS` (Ha A-D, LT A-D, LT finale, BF IIIa/b, termes DE : Grabhügel, Ringwall, Viereckschanze, Fürstengrab/sitz)
- [x] 5.2 Implémenter `extract_periods()` pour détecter toutes les mentions chronologiques (Fer et non-Fer) incluant termes germaniques (eisenzeit, latènezeit)
- [x] 5.3 Implémenter `normalize_period()` : mapping des mentions brutes vers un vocabulaire contrôlé (Ha A, Ha B, Ha C, Ha D1, Ha D2, Ha D3, LT A, LT B, LT C, LT D, BF III, Néolithique, Gallo-romain, etc.)
- [x] 5.4 Implémenter `extract_vestiges()` et `guess_type()` dans `src/extraction/record_builder.py` — hiérarchie : oppidum > sanctuaire > nécropole > tumulus > sépulture > habitat > atelier > dépôt > indéterminé. Inclure termes DE (Siedlung, Brandgrab, etc.)
- [x] 5.5 Implémenter `_estimate_confidence()` : heuristique HIGH/MEDIUM/LOW basée sur fouille récente, nb de refs biblio, présence de figures
- [x] 5.6 Implémenter `build_record()` pour construire un `SiteRecord` complet (avec confidence_level) à partir d'une `SubNotice`

## 6. Pipeline orchestration

- [x] 6.1 Implémenter `Pipeline.run()` dans `src/extraction/pipeline.py` : enchaînement des 4 phases avec logging Rich
- [x] 6.2 Ajouter des compteurs de progression (pages lues, communes détectées, sous-notices filtrées)
- [x] 6.3 Écrire un résumé d'extraction en fin de pipeline (totaux, temps, taux de couverture)
- [x] 6.4 Calculer et afficher les métriques de qualité : % pages avec commune détectée, distribution nb sous-notices/commune, outliers (communes avec 0 sous-notice), distribution longueur notices

## 7. Stockage DuckDB

- [x] 7.1 Implémenter `create_schema()` dans `src/storage/schema.py` : 6 tables (avec FK REFERENCES, confidence_level, periode_norm) + 5 vues (inclut v_period_cooccurrence) avec CREATE IF NOT EXISTS
- [x] 7.2 Implémenter `load_records()` dans `src/storage/loader.py` : insertion SiteRecord → notices + tables liées, upsert via `INSERT ... ON CONFLICT DO UPDATE` ou DELETE/INSERT transactionnel
- [x] 7.3 Implémenter `load_communes()` dans `src/storage/loader.py` : insertion métadonnées communes (id, name, page_start, page_end)
- [x] 7.4 Implémenter les requêtes analytiques dans `src/storage/queries.py` : top_communes, search_notices, period_distribution (sur periode_norm), vestige_frequency, total_counts, period_cooccurrence, extraction_metrics

## 8. Géocodage communes

- [x] 8.1 Implémenter le géocodage BAN dans `src/storage/queries.py` (ou un `src/geocoding.py` dédié) : requête httpx throttled, parsing résultat JSON
- [x] 8.2 Implémenter la reprojection WGS84 → Lambert-93 via pyproj
- [x] 8.3 Implémenter la lecture/écriture du cache `communes_geo.json` en GeoJSON FeatureCollection
- [x] 8.4 Implémenter le mode incrémental (ne re-géocoder que les communes sans coordonnées)

## 9. CLI Click

- [x] 9.1 Implémenter le CLI dans `src/__main__.py` avec le groupe Click et la commande `extract`
- [x] 9.2 Ajouter la commande `geocode`
- [x] 9.3 Ajouter la commande `export` avec options `--format`, `--output`, `--all`
- [x] 9.4 Ajouter la commande `stats` avec affichage Rich (table, compteurs)
- [x] 9.5 Ajouter la commande `eda` : EDA rapide post-extraction — distributions (notices/commune, longueur texte, périodes, types), détection outliers, export histogrammes PNG

## 10. Interface Dash — Structure et thème

- [x] 10.1 Implémenter `create_app()` dans `src/ui/app.py` : Dash factory, thème DARKLY, Inter font, pages auto-discovery
- [x] 10.2 Implémenter le layout principal dans `src/ui/layout.py` : navbar avec liens des 4 pages, container pour le contenu
- [x] 10.3 Compléter `assets/cag.css` avec le thème sombre archéologique complet (background, surface, accents, polices)

## 11. Interface Dash — Page Carte

- [x] 11.1 Implémenter `pages/carte.py` : Scattermapbox centré Bas-Rhin, points communes, sizing par nombre de notices
- [x] 11.2 Ajouter les filtres latéraux (type de site, période, nombre de notices minimum)
- [x] 11.3 Implémenter le callback de clic commune → panneau détail avec liste des sous-notices
- [x] 11.4 Créer le composant `components/commune_map.py` pour encapsuler la logique carte

## 12. Interface Dash — Page Notices

- [x] 12.1 Implémenter `pages/notices.py` : layout deux panneaux (liste gauche, détail droite)
- [x] 12.2 Implémenter la liste scrollable des communes avec recherche texte et toggle "Fer uniquement"
- [x] 12.3 Implémenter le panneau détail : texte complet, highlight mots-clés Fer, tags période/vestige, refs biblio
- [x] 12.4 Créer le composant `components/notice_card.py` pour le rendu d'une notice individuelle

## 13. Interface Dash — Page Chronologie

- [x] 13.1 Implémenter `pages/chronologie.py` : bar chart horizontal de toutes les périodes
- [x] 13.2 Ajouter le chart détaillé des sous-périodes Fer (Ha C, Ha D1-D3, LT A-D)
- [x] 13.3 Implémenter le heatmap de co-occurrences entre périodes normalisées (via vue `v_period_cooccurrence`)
- [x] 13.4 Créer le composant `components/period_chart.py`

## 14. Interface Dash — Page Statistiques

- [x] 14.1 Implémenter `pages/stats.py` : 4 KPI cards (communes, notices, Fer, figures)
- [x] 14.2 Ajouter le donut chart des types de sites
- [x] 14.3 Ajouter le bar chart top 20 communes
- [x] 14.4 Ajouter le treemap des fréquences de vestiges
- [x] 14.5 Ajouter le bar chart de distribution des niveaux de confiance (HIGH/MEDIUM/LOW)
- [x] 14.6 Créer le composant `components/type_chart.py`

## 15. Export pipeline parent

- [x] 15.1 Implémenter `export_to_raw_records()` dans `src/export/to_raw_records.py` : requête DuckDB → dicts RawRecord-compatible
- [x] 15.2 Ajouter le support `--all` pour exporter toutes les notices (pas uniquement Fer)
- [x] 15.3 Générer le JSON avec indentation et encodage UTF-8

## 16. Tests unitaires

- [x] 16.1 Créer `tests/fixtures/sample_pages.json` avec le texte extrait de 10 pages représentatives
- [x] 16.2 Implémenter `tests/test_pdf_reader.py` : extraction texte, 2 colonnes, tables, page range
- [x] 16.3 Implémenter `tests/test_commune_splitter.py` : split communes, multi-pages, edge cases
- [x] 16.4 Implémenter `tests/test_notice_parser.py` : sous-notices N*, (NNN XX), lieu-dits, biblio
- [x] 16.5 Implémenter `tests/test_iron_age_filter.py` : filtre Fer (Ha A-D, LT A-D, termes DE), exclusion gallo-romain, mixed periods
- [x] 16.6 Implémenter `tests/test_record_builder.py` : construction SiteRecord, guess_type (tumulus vs nécropole, sanctuaire), confidence_level, troncature, normalize_period
- [x] 16.7 Implémenter `tests/test_duckdb_storage.py` : schéma, insert, vues, queries, idempotence

## 17. Intégration et documentation

- [x] 17.1 Mettre à jour `README.md` du sous-projet avec les instructions d'installation et d'utilisation complètes
- [x] 17.2 Vérifier le `.gitignore` : `data/cag67.duckdb`, `data/communes_geo.json`, `__pycache__`
- [x] 17.3 Tester le workflow complet : install → extract → geocode → UI → export
- [x] 17.4 Push final vers `BaseFerRhin/CAG-Bas-Rhin`
