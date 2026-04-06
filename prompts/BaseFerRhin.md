# BaseFerRhin — Inventaire normalisé des sites de l'âge du Fer du Rhin supérieur

## CONTEXTE

Assistant expert en archéologie protohistorique européenne, data engineering et normalisation de bases patrimoniales.

Objectif : construire un inventaire normalisé des sites de l'âge du Fer couvrant le Rhin supérieur :
- **Alsace** (Bas-Rhin 67, Haut-Rhin 68 — France)
- **Bade-Wurtemberg** (Südbaden, Freiburg — Allemagne)
- **Canton de Bâle** (Bâle-Ville, Bâle-Campagne — Suisse)

Périodes : Hallstatt (env. -800 à -450) et La Tène (env. -450 à -25)

---

## SOURCES DE DONNÉES

### Sources primaires — Gallica (BnF)

| Source | ARK / URL | Type | Contenu |
|--------|-----------|------|---------|
| **CAG 67/1 — Bas-Rhin** (Flotté & Fuchs, 2000) | `ark:/12148/bd6t542071728` — [SRU](https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&exactSearch=true&collapsing=false&version=1.2&query=(notice%20all%20%22carte%20arch%C3%A9ologique%20de%20la%20Gaule%22%20and%20dc.subject%20all%20%22bas-rhin%22%20)) | Inventaire par commune | 735 p., 587 fig. — notices archéo de la Protohistoire à Charlemagne, classées par commune |
| **CAG 68 — Haut-Rhin** (Zehner, 1998) | [SRU](https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&exactSearch=true&collapsing=false&version=1.2&query=notice%20all%20%22carte%20arch%C3%A9ologique%20de%20la%20Gaule%20Haut-Rhin%22) | Inventaire par commune | 375 p., 234 fig. — même structure que CAG 67 |
| **Cahiers alsaciens d'archéologie, d'art et d'histoire** | `ark:/12148/cb343831065` — [46 ans numérisés](https://gallica.bnf.fr/ark:/12148/cb343831065/date) | Périodique | Articles de fouilles, inventaires, cartes de répartition (depuis 1957) |
| **Déchelette — Manuel d'archéo. celtique (Hallstatt)** | `ark:/12148/bpt6k6106092j` | Ouvrage de référence | Typologie fondamentale du Premier âge du Fer |

#### APIs Gallica utilisées

- **SRU Search** (`/services/engine/search/sru`) — Recherche par mots-clés CQL dans les métadonnées
- **OCR Text** (`/ark:/{id}/f{page}.texteBrut`) — Extraction texte brut page par page
- **ALTO XML** (`/RequestDigitalElement?O={id}&E=ALTO&Deb={page}`) — OCR structuré avec coordonnées
- **IIIF Image** (`/iiif/ark:/{id}/f{page}/...`) — Récupération cartes et planches
- **Wrapper Python** : [`PyGallica`](https://github.com/ian-nai/PyGallica)

### Sources complémentaires (hors Gallica)

| Source | URL | Couverture |
|--------|-----|------------|
| Persée | persee.fr | Publications académiques FR récentes |
| HAL Archives ouvertes | hal.science | Thèses, articles métallurgie du fer |
| Archéologie Alsace (catalogue) | archeologie-alsace.centredoc.fr | 687 docs d'inventaire |
| Atlas des Patrimoines (Mérimée/Patriarche) | atlas.patrimoines.culture.fr | Base nationale des sites |
| iDAI.gazetteer (DAI) | gazetteer.dainst.org | Sites archéologiques DE |
| geo.admin.ch | geo.admin.ch | Sites archéologiques CH |
| ARACHNE (Köln) | arachne.dainst.org | Objets et sites DE |

---

## 1. MODÈLE DE DONNÉES (DDD)

Architecture en agrégats : `Site` → `PhaseOccupation[]` → `Source[]`

### Agrégat `Site` (entité racine)

| Champ | Type | Contrainte | Description |
|-------|------|-----------|-------------|
| `site_id` | str | PK, préfixé | Identifiant unique stable (ex: `CAG67-STRASBOURG-042`) |
| `nom_site` | str | requis | Nom principal du site |
| `variantes_nom` | list[str] | | Autres appellations (FR/DE historiques) |
| `pays` | str | enum: FR/DE/CH | |
| `region_admin` | str | enum | Alsace / Baden-Württemberg / Basel-Stadt / Basel-Landschaft |
| `commune` | str | requis | Nom actuel de la commune |
| `latitude` | float | nullable | WGS84 |
| `longitude` | float | nullable | WGS84 |
| `precision_localisation` | enum | requis | `exact` / `approx` / `centroide` |
| `type_site` | enum | requis | Voir nomenclature §3 |
| `description` | str | | Texte libre |
| `surface_m2` | float | nullable | Surface estimée en m² |
| `altitude_m` | float | nullable | Altitude en mètres |
| `statut_fouille` | enum | | `fouille` / `prospection` / `signalement` / `archivé` |
| `identifiants_externes` | dict | | `{patriarche: ..., wikidata: ..., idai: ...}` |
| `commentaire_qualite` | str | | |
| `date_creation` | datetime | auto | |
| `date_maj` | datetime | auto | |

### Entité `PhaseOccupation`

Un site peut avoir **plusieurs phases** (ex: Hallstatt D + La Tène A).

| Champ | Type | Contrainte | Description |
|-------|------|-----------|-------------|
| `phase_id` | str | PK | |
| `site_id` | str | FK → Site | |
| `periode` | enum | requis | Hallstatt / La Tène / transition / indéterminé |
| `sous_periode` | str | nullable | Ha C, Ha D1, Ha D2-D3, LT A, LT B, LT C, LT D |
| `datation_debut` | int | nullable | Année (négatif = av. J.-C.) |
| `datation_fin` | int | nullable | |
| `methode_datation` | str | | typologie / C14 / dendro / thermoluminescence |
| `mobilier_associe` | list[str] | | céramique, métal, verre, os, monnaie, fibule... |

### Entité `Source`

Relation 1:N — un site peut provenir de **plusieurs sources**.

| Champ | Type | Contrainte | Description |
|-------|------|-----------|-------------|
| `source_id` | str | PK | |
| `site_id` | str | FK → Site | |
| `reference` | str | requis | Référence bibliographique complète |
| `type_source` | enum | | `gallica_cag` / `gallica_periodique` / `gallica_ouvrage` / `carte` / `tableur` / `publication` / `rapport_fouille` |
| `url` | str | nullable | |
| `ark_gallica` | str | nullable | Identifiant ARK BnF |
| `page_gallica` | int | nullable | Numéro de page dans le document Gallica |
| `niveau_confiance` | enum | requis | `élevé` / `moyen` / `faible` |
| `confiance_ocr` | float | nullable | Score de qualité OCR (0.0–1.0) |
| `date_extraction` | datetime | auto | |

---

## 2. PIPELINE ETL

### Architecture (Clean Architecture)

```
application/        → Use cases (orchestration du pipeline)
domain/             → Modèles, normaliseurs, validateurs (AUCUNE dépendance externe)
infrastructure/     → Extracteurs (Gallica, PDF, CSV), géocodage, persistance
```

### Étapes du pipeline

```
1. DISCOVER    → Interroger Gallica SRU pour lister les documents pertinents
2. INGEST      → Télécharger les pages OCR / ALTO / images via APIs Gallica
3. EXTRACT     → Parser le texte (PDF, OCR brut, CSV)
4. NORMALIZE   → Harmoniser types, périodes, toponymes (FR/DE)
5. DEDUPLICATE → Fuzzy matching (nom + commune + coordonnées)
6. GEOCODE     → Multi-API : Nominatim (FR), BKG (DE), geo.admin.ch (CH)
7. VALIDATE    → Cohérence chrono-géographique
8. EXPORT      → GeoJSON + CSV + SQLite (+ PostGIS optionnel)
```

### Principes

- **Idempotence** : chaque étape est rejouable sans créer de doublons
- **Incrémental** : ajout de nouvelles sources sans tout recalculer
- **Traçabilité** : chaque transformation est loguée (source → résultat)
- **Gestion d'erreurs** : les échecs (OCR illisible, géocodage KO) vont dans une file de révision manuelle
- **Library-first** : `pdfplumber`, `rapidfuzz`, `geopy`, `pydantic` (pas de code custom inutile)

### Spécificités Gallica

Le pipeline Gallica suit un flux dédié :

```
SRU Search (mots-clés) → Liste d'ARK IDs
    → Pour chaque ARK :
        → Récupérer métadonnées (titre, auteur, date)
        → Pour chaque page pertinente :
            → Télécharger OCR (.texteBrut)
            → Évaluer qualité OCR (ratio mots reconnus / total)
            → Si qualité < seuil → télécharger ALTO XML (coordonnées)
            → Si carte/figure → télécharger via IIIF Image
        → Extraire les mentions de sites (NER + regex)
        → Normaliser et injecter dans le pipeline principal
```

---

## 3. NORMALISATION

### Types de sites (nomenclature standard)

| Code | FR | DE | Alias fréquents |
|------|----|----|-----------------|
| `OPPIDUM` | Oppidum | Oppidum | fortification, enceinte, Höhensiedlung |
| `HABITAT` | Habitat | Siedlung | village, établissement, Gehöft |
| `NECROPOLE` | Nécropole | Gräberfeld | cimetière, tumulus, Grabhügel, Hügelgrab |
| `DEPOT` | Dépôt | Hortfund | trésor, cachette, Depotfund |
| `SANCTUAIRE` | Sanctuaire | Heiligtum | lieu de culte, Kultstätte, Viereckschanze |
| `ATELIER` | Atelier | Werkstatt | forge, officine, Verhüttungsplatz |
| `VOIE` | Voie | Weg | chemin, route, Straße |
| `TUMULUS` | Tumulus | Grabhügel | tertre, butte, Hügelgrab |
| `INDETERMINE` | Indéterminé | Unbestimmt | inconnu, non classé |

### Périodes (avec sous-périodes)

| Code | Sous-périodes | Dates approx. |
|------|--------------|---------------|
| `HALLSTATT` | Ha C, Ha D1, Ha D2, Ha D3 | -800 à -450 |
| `LA_TENE` | LT A, LT B1, LT B2, LT C1, LT C2, LT D1, LT D2 | -450 à -25 |
| `TRANSITION` | Ha D3 / LT A | -500 à -400 |
| `INDETERMINE` | — | — |

### Concordance toponymique FR/DE (Alsace)

Essentielle pour les sources XIXe–XXe où l'Alsace change de langue administrative.

| FR actuel | DE historique | Notes |
|-----------|--------------|-------|
| Strasbourg | Straßburg | |
| Colmar | Kolmar | |
| Mulhouse | Mülhausen | |
| Haguenau | Hagenau | |
| Brumath | Brumath | Brocomagus (antique) |
| Saverne | Zabern | |
| Sélestat | Schlettstadt | |
| Wissembourg | Weißenburg | |
| Biesheim | Biesheim | Oedenburg/Kunheim (site archéo) |
| Sainte-Croix-en-Plaine | Heiligkreuz | |
| Breisach (DE) | Breisach | Mont Isteiner Klotz |
| Basel (CH) | Basel/Bâle | Münsterhügel |

---

## 4. CODE ATTENDU

### Structure de projet (Clean Architecture)

```
BaseFerRhin/
├── src/
│   ├── domain/
│   │   ├── models/          Site, PhaseOccupation, Source (Pydantic)
│   │   ├── normalizers/     type_site, periode, toponymie
│   │   └── validators/      cohérence chrono + géo
│   ├── infrastructure/
│   │   ├── extractors/      gallica (SRU+OCR+IIIF), pdf, csv
│   │   ├── geocoding/       multi-API (Nominatim, BAN, geo.admin.ch)
│   │   └── persistence/     SQLite repository, GeoJSON exporter
│   └── application/
│       └── pipeline.py      Orchestration ETL
├── data/
│   ├── raw/                 Sources brutes téléchargées
│   ├── processed/           Données normalisées
│   ├── reference/           Dictionnaires, concordances JSON
│   └── output/              GeoJSON, CSV, SQLite
├── tests/
│   ├── domain/              Tests normaliseurs + validateurs
│   ├── infrastructure/      Tests extracteurs (mocks)
│   └── fixtures/            Golden dataset de test
├── notebooks/               Exploration, visualisation carto
├── prompts/                 Ce fichier
├── pyproject.toml
└── README.md
```

### Dépendances principales

- `pydantic` — Validation du modèle de données
- `pdfplumber` — Extraction PDF
- `rapidfuzz` — Fuzzy matching pour déduplication
- `geopy` — Géocodage multi-API
- `httpx` — Client HTTP async pour APIs Gallica
- `lxml` — Parsing ALTO XML
- `rich` — Logging structuré
- `geopandas` — Export GeoJSON
- `sqlite-utils` — Persistance SQLite

### Tests requis

- Tests unitaires : normaliseurs (type_site, période, toponymie)
- Tests unitaires : validateurs (cohérence chrono, cohérence géo)
- Tests d'intégration : extracteur Gallica (mocks HTTP)
- Tests de régression : déduplication (golden dataset de 20 sites connus)
- Couverture cible : >80% sur le domaine

---

## 5. CRITÈRES D'ACCEPTANCE

1. Le modèle Pydantic valide un site avec phases multiples et sources multiples
2. L'extracteur Gallica récupère les pages OCR de la CAG 67 et CAG 68
3. Le normaliseur classifie correctement "Höhensiedlung" → `OPPIDUM`
4. La déduplication fusionne "Breisach am Rhein" et "Vieux-Brisach" en un seul site
5. L'export GeoJSON est valide et affichable dans QGIS / geojson.io
6. Le pipeline complet tourne en < 10 min pour 100 sites de test
