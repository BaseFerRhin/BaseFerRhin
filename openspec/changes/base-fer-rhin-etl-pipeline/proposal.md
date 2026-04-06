## Why

Les données archéologiques de l'âge du Fer dans le Rhin supérieur (Alsace, Bade-Wurtemberg, Canton de Bâle) sont dispersées dans des sources hétérogènes — publications numérisées sur Gallica (CAG 67, CAG 68, Cahiers alsaciens), inventaires PDF, fichiers tabulaires, cartes — sans base unifiée permettant l'analyse spatiale et la comparaison inter-régionale. La numérisation récente (2025) de la Carte archéologique de la Gaule sur Gallica crée une opportunité d'extraction automatisée via les APIs SRU/OCR/IIIF de la BnF.

## What Changes

- Création d'un **modèle de données DDD** (agrégats Pydantic : Site → PhaseOccupation[] → Source[]) couvrant les périodes Hallstatt (-800/-450) et La Tène (-450/-25)
- Implémentation d'un **extracteur Gallica** exploitant les APIs SRU Search, OCR Text, ALTO XML et IIIF Image pour la CAG Bas-Rhin (ark:/12148/bd6t542071728), la CAG Haut-Rhin, et les Cahiers alsaciens (ark:/12148/cb343831065)
- Implémentation d'**extracteurs complémentaires** pour PDF locaux et fichiers CSV
- Développement de **normaliseurs bilingues FR/DE** pour les types de sites, périodes chronologiques et toponymes alsaciens
- Construction d'un **pipeline ETL à 8 étapes** (discover → ingest → extract → normalize → deduplicate → geocode → validate → export) idempotent et incrémental
- Mise en place d'un **géocodeur multi-API** (Nominatim FR, BKG DE, geo.admin.ch CH)
- Export en **GeoJSON, CSV et SQLite** pour exploitation SIG (QGIS)

## Capabilities

### New Capabilities

- `domain-model`: Modèle de données Pydantic (Site, PhaseOccupation, Source) avec enums normalisés (TypeSite, Periode, NiveauConfiance) et validation de cohérence chrono-géographique
- `gallica-extractor`: Extraction de données archéologiques depuis les APIs Gallica (SRU Search, OCR Text, ALTO XML, IIIF Image) avec évaluation de qualité OCR et gestion des identifiants ARK
- `source-extractors`: Extracteurs pour PDF locaux (pdfplumber) et fichiers CSV avec interface commune
- `site-normalizer`: Normalisation bilingue FR/DE des types de sites, périodes, sous-périodes et toponymes alsaciens historiques
- `site-deduplicator`: Déduplication par fuzzy matching multi-critères (nom + commune + coordonnées) via rapidfuzz
- `multi-geocoder`: Géocodage adaptatif selon le pays (Nominatim/BAN pour FR, BKG pour DE, geo.admin.ch pour CH) avec fallback et file de révision manuelle
- `etl-pipeline`: Orchestration des 8 étapes du pipeline avec idempotence, mode incrémental, traçabilité et gestion d'erreurs
- `data-export`: Export multi-format (GeoJSON, CSV, SQLite) avec validation de schéma et compatibilité QGIS

### Modified Capabilities

_(Aucune — projet nouveau, pas de specs existantes)_

## Impact

- **Code** : Nouveau projet Python dans `src/` structuré en Clean Architecture (domain / infrastructure / application)
- **Dépendances** : pydantic, httpx, tenacity, pdfplumber, rapidfuzz, geopy, lxml, geopandas, sqlite-utils, rich
- **APIs externes** : Gallica (BnF), Nominatim (OSM), BAN (FR), geo.admin.ch (CH) — toutes gratuites et ouvertes
- **Données** : Stockage local dans `data/` (raw, processed, reference, output) — pas de base distante
- **Tests** : Suite pytest avec mocks HTTP pour Gallica, golden dataset de 20 sites connus, couverture >80% sur le domaine
