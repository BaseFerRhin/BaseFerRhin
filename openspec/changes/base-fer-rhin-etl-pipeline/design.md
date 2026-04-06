## Context

Le Rhin supérieur (Alsace, Südbaden, Canton de Bâle) est l'une des régions les plus riches en vestiges de l'âge du Fer en Europe. Les données sont dispersées dans :
- La **Carte archéologique de la Gaule** (CAG 67 et 68), récemment numérisée sur Gallica
- Les **Cahiers alsaciens d'archéologie** (46 ans de publications numérisées)
- Des publications académiques, rapports de fouilles, inventaires tabulaires

Aucune base unifiée n'existe pour croiser ces sources. Le projet construit un pipeline ETL Python suivant les principes Clean Architecture / DDD, avec un extracteur dédié aux APIs Gallica (SRU, OCR, IIIF).

**Contraintes :**
- Sources multilingues (FR/DE) avec toponymes historiques changeants (Alsace)
- OCR de qualité variable sur les documents anciens Gallica (pré-1950)
- 3 pays, 3 systèmes de géocodage différents
- Volume estimé : 500–2000 sites, évolutif par ajout de sources

## Goals / Non-Goals

**Goals :**
- Produire un inventaire normalisé, géocodé et dédupliqué des sites de l'âge du Fer du Rhin supérieur
- Exploiter les APIs Gallica pour extraire automatiquement les données de la CAG 67, CAG 68 et des Cahiers alsaciens
- Permettre l'enrichissement incrémental par ajout de nouvelles sources sans recalcul complet
- Exporter en formats exploitables par les archéologues (GeoJSON/QGIS, CSV, SQLite)

**Non-Goals :**
- Pas d'interface web ou de visualisation cartographique intégrée (QGIS externe)
- Pas de NLP/NER avancé pour l'extraction sémantique (regex + patterns suffisent en v1)
- Pas de connexion à une base PostGIS distante (SQLite local suffit en v1)
- Pas de couverture des périodes hors âge du Fer (Protohistoire stricte : Hallstatt + La Tène)
- Pas d'intégration aux bases institutionnelles (Patriarche, ARACHNE) — identifiants externes stockés mais pas de sync

## Decisions

### D1 : Clean Architecture en 3 couches (domain / infrastructure / application)

**Choix** : Séparation stricte en `domain/` (modèles Pydantic, normaliseurs, validateurs — zéro import externe), `infrastructure/` (extracteurs HTTP, géocodeurs, persistance), `application/` (orchestration pipeline).

**Alternatives considérées :**
- Script monolithique : rapide mais non maintenable, couplage fort
- Framework ETL (Airflow, Prefect) : overkill pour le volume actuel

**Rationale** : Le domaine archéologique (normalisation des types, cohérence chronologique) est la logique métier centrale. Elle doit rester testable indépendamment des APIs externes.

### D2 : Pydantic comme modèle de domaine

**Choix** : `pydantic.BaseModel` pour Site, PhaseOccupation, Source avec enums stricts et validation intégrée.

**Alternatives considérées :**
- dataclasses : pas de validation native
- SQLAlchemy models : couplage à la persistance
- attrs : moins adopté, pas de sérialisation JSON native

**Rationale** : Pydantic offre validation, sérialisation JSON, et documentation automatique du schéma. Le modèle reste pur (aucune dépendance infrastructure).

### D3 : httpx async pour les APIs Gallica

**Choix** : `httpx.AsyncClient` avec retry via `tenacity` pour les appels SRU, OCR et IIIF.

**Alternatives considérées :**
- PyGallica : wrapper existant mais non maintenu, synchrone uniquement
- requests : pas d'async natif, problématique pour le scraping multi-pages

**Rationale** : La CAG 67 fait 735 pages — le téléchargement séquentiel serait trop lent. httpx async + semaphore (max 5 concurrent) respecte Gallica tout en étant performant.

### D4 : Modèle multi-phases par site

**Choix** : Relation 1:N `Site → PhaseOccupation[]` au lieu d'un champ `periode` unique.

**Rationale** : De nombreux sites du Rhin supérieur ont une occupation multi-phases (ex : Breisach — Hallstatt D + La Tène A). Un champ unique perdrait cette information cruciale.

### D5 : Géocodage adaptatif par pays

**Choix** : Dispatch automatique vers BAN (FR), Nominatim avec filtre pays (DE), geo.admin.ch (CH). BKG (Bundesamt für Kartographie) est identifié comme amélioration v2 pour les lieux-dits allemands non couverts par Nominatim.

**Alternatives considérées :**
- Nominatim seul : couverture insuffisante pour les petits lieux-dits suisses
- BKG d'emblée : API nécessitant une clé, complexité d'intégration non justifiée en v1
- Google Geocoding API : payant, non justifié pour des données académiques

**Rationale** : Nominatim avec `countrycodes=de` offre une couverture suffisante pour les communes allemandes du Rhin supérieur en v1. BAN est optimal pour la France, geo.admin.ch pour la Suisse. Le fallback Nominatim générique assure une couverture minimale.

### D6 : Déduplication multi-critères avec rapidfuzz

**Choix** : Score composite (nom 40%, commune 30%, coordonnées 30%) via `rapidfuzz.fuzz.token_sort_ratio` + distance géographique Haversine.

**Rationale** : Les mêmes sites apparaissent avec des noms différents selon les sources (FR/DE, variantes orthographiques). Le fuzzy matching est indispensable. `rapidfuzz` est 10x plus rapide que `fuzzywuzzy` (implémentation C).

### D7 : SQLite + GeoJSON comme formats de sortie

**Choix** : `sqlite-utils` pour la persistance relationnelle, `geopandas` pour l'export GeoJSON.

**Rationale** : SQLite est portable (fichier unique), versionnable, et suffisant pour le volume. GeoJSON est le standard d'échange SIG le plus universel (QGIS, Leaflet, geojson.io).

## Risks / Trade-offs

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| OCR illisible sur pages anciennes de la CAG | Haute | Données manquantes | Score de confiance OCR par page ; seuil configurable ; file de révision manuelle |
| Rate limiting Gallica (pas de clé API) | Moyenne | Pipeline bloqué | Semaphore async (max 5 req/s) ; cache local des pages déjà téléchargées ; retry exponentiel |
| Faux positifs en déduplication (sites homonymes de communes différentes) | Moyenne | Fusions erronées | Seuil de confiance configurable ; revue manuelle au-dessus de 70% et en-dessous de 95% |
| Toponymes introuvables par géocodeur (lieux-dits disparus) | Haute | Coordonnées manquantes | Fallback sur centroïde communal ; champ `precision_localisation` = `centroide` |
| Changement d'API Gallica (structure des URLs) | Faible | Extracteur cassé | Abstraction via interface ; tests d'intégration avec mocks + 1 test end-to-end optionnel |
| Volume sous-estimé (>2000 sites) | Faible | Lenteur pipeline | Architecture async ; mode incrémental avec cache SQLite |

## Open Questions

1. **Seuil OCR** : À quel score de confiance OCR marque-t-on une page comme « illisible » ? Proposé : 0.4 (< 40% de mots reconnus).
2. **CAG Haut-Rhin ARK** : L'identifiant ARK exact du volume CAG 68 sur Gallica reste à confirmer via la requête SRU — le volume est référencé mais l'ARK direct n'a pas encore été isolé.
3. **Licence données Gallica** : Les métadonnées sont sous Licence Ouverte. Les textes OCR extraits sont-ils réutilisables dans une base dérivée ? À confirmer avec les CGU BnF.
4. **Couverture allemande v2** : Faut-il prévoir dès maintenant une interface pour les données FREIBURG ADAB / iDAI.gazetteer, ou attendre une phase ultérieure ?
