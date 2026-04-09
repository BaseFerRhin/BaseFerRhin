# Relations inter-fichiers — Analyse croisée des 15 sources `data/input/`

> Mis à jour : 2026-04-09 — Intègre les 15 fichiers (2 CSV, 7 XLSX, 1 ODS, 2 DBF, 3 DOC)

---

## 1. Inventaire des sources

| # | Fichier | Format | Lignes | Cols | Coords | Période | Grain |
|---|---------|--------|--------|------|--------|---------|-------|
| 1 | `20250806_LoupBernard_ArkeoGis.csv` | CSV | 116 | 23 | WGS84 | Hallstatt–La Tène | Site |
| 2 | `20250806_ADAB2011_ArkeoGis.csv` | CSV | 656 | 23 | WGS84 | Multi-période | Site |
| 3 | `Alsace_Basel_AF (1).xlsx` | XLSX | 1083 | 16 | WGS84 + UTM32N | Âge du Fer | Site |
| 4 | `BdD_Proto_Alsace (1).xlsx` | XLSX | 1127 | 23 | Non | Protohistoire | Site |
| 5 | `20250806_Patriarche_ageFer.xlsx` | XLSX | 836 | 5 | Non | Âge du Fer | EA (entité archéo.) |
| 6 | `20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx` | XLSX | 339 | 37 | L93 | BF IIIb–Ha D3 | Nécropole |
| 7 | `20240425_mobilier_sepult_def (1).ods` | ODS | 310 | 91 | L93 | Hallstatt | Sépulture |
| 8 | `20240419_Inhumations silos (1).xlsx` | XLSX | 86 | 94 | L93 | BF–Ha | Individu (inhumation) |
| 9 | `20240425_habitats-tombes riches_Als-Lor (1).xlsx` | XLSX | 110 | 21 | Non | Hallstatt–La Tène | Site élite |
| 10 | `BDD-fun_AFEAF24-total_04.12 (1).xlsx` | XLSX | 401 | 63 | Non | Multi-période | Sépulture/Site funéraire |
| 11 | `2026_afeaf_lineaire.dbf` | DBF | 27 | 9 | Non (shapefile) | Âge du Fer | Entité linéaire |
| 12 | `ea_fr.dbf` | DBF | 42 | 29 | Non | BZ–Fer | EA (entité archéo.) |
| 13 | `cag_68_texte.doc` | DOC | — | — | Non | Multi-période | Notice communale |
| 14 | `cag_68_index.doc` | DOC | — | — | Non | — | Index |
| 15 | `cag_68_biblio.doc` | DOC | — | — | Non | — | Bibliographie |

**Total** : ~5 133 lignes de données structurées + 3 documents Word (CAG 68)

---

## 2. Groupes thématiques

### 2.1 Inventaires de sites (généralistes)

Fichiers fournissant une couverture large de sites archéologiques :

| Fichier | Zone | Spécificité |
|---------|------|-------------|
| `LoupBernard_ArkeoGis` | Bade-Wurtemberg | Oppida/enceintes, haute qualité, 100% daté |
| `ADAB2011_ArkeoGis` | Nordbaden | Inventaire archéologique large, 28.8% daté |
| `Alsace_Basel_AF` | Alsace + Bâle | 1083 sites ÂF, coordonnées, le plus gros jeu structuré |
| `BdD_Proto_Alsace` | Alsace | 1127 sites proto, riche en typologie, sans coords |
| `Patriarche_ageFer` | Bas-Rhin (67) | 836 EA nationales, identifiants officiels, sans coords |
| `ea_fr.dbf` | Bas-Rhin (67) | 42 EA, riche en champs (vestiges, géométrie) |

**Stratégie de fusion** : `Alsace_Basel_AF` comme source géographique pivot → enrichir avec `BdD_Proto_Alsace` (typologie) + `Patriarche` (codes EA officiels) + `ea_fr` (détails vestiges).

### 2.2 Bases funéraires (nécropoles, sépultures)

| Fichier | Zone | Grain | Spécificité |
|---------|------|-------|-------------|
| `necropoles_BFIIIb-HaD3` | Alsace-Lorraine | Nécropole | 339 nécropoles, chronologie fine BF III–Ha D3 |
| `mobilier_sepult_def` | Alsace | Sépulture | 310 tombes, 91 colonnes de mobilier |
| `Inhumations silos` | Alsace-Lorraine | Individu | 86 inhumations en silo, anthropologie détaillée |
| `habitats-tombes riches` | Alsace-Lorraine | Site | 110 sites d'élite, armement/or/char/imports |
| `BDD-fun_AFEAF24` | Multi-région | Sépulture/Site | 401 entrées, NMI et dépôts |

**Stratégie** : Agréger au niveau site pour alimenter `sites.csv`, puis conserver les données détaillées (sépultures, mobilier, individus) dans des tables liées.

### 2.3 Sources documentaires (CAG 68)

| Fichier | Contenu | Priorité |
|---------|---------|----------|
| `cag_68_texte.doc` | Notices communales archéologiques Haut-Rhin | HAUTE — structure ~CAG 67/1 |
| `cag_68_index.doc` | Index des sites et communes | MOYENNE — aide au parsing |
| `cag_68_biblio.doc` | Bibliographie complète | BASSE — enrichissement |

**Stratégie** : Conversion `.doc` → texte, puis extraction NER par commune, parallèle au sous-projet `CAG Bas-Rhin/`.

---

## 3. Recouvrement géographique

### 3.1 Systèmes de coordonnées

| Fichier | Projection | Remarque |
|---------|-----------|----------|
| `LoupBernard`, `ADAB2011` | WGS84 (lat/lon) | Prêt à l'emploi |
| `Alsace_Basel_AF` | WGS84 + UTM 32N (EPSG:25832) | Nécessite reprojection UTM→WGS84 |
| `necropoles_BFIIIb-HaD3`, `mobilier_sepult_def`, `Inhumations silos` | Lambert-93 (EPSG:2154) | Reprojection L93→WGS84 |
| `Patriarche`, `BdD_Proto_Alsace`, `habitats-tombes riches`, `BDD-fun_AFEAF24`, DBFs | Aucun | Géocodage par commune nécessaire |

### 3.2 Emprise spatiale

| Source | Emprise lat | Emprise lon | Zone approximative |
|--------|------------|-------------|-------------------|
| LoupBernard | 47.58–49.20 | 6.57–9.85 | Bade-Wurtemberg large |
| ADAB2011 | 48.02–48.78 | 8.17–9.46 | Nordbaden strict |
| Alsace_Basel_AF | 47.38–48.97 | 6.84–8.23 | Alsace + Bâle |
| necropoles (L93) | Y ~687k–6935k | X ~943k–1063k | Alsace-Lorraine |
| mobilier_sepult (L93) | Y ~6762k–6915k | X ~991k–1043k | Alsace |
| Inhumations (L93) | Y ~6745k–6867k | X ~931k–1065k | Alsace-Lorraine |

**Zone de chevauchement principale** : corridor rhénan entre Bâle (47.5°N) et Strasbourg (48.6°N), soit exactement la zone cible du projet BaseFerRhin.

### 3.3 Paires de recouvrement potentiel

| Source A | Source B | Type de lien | Clé de jointure |
|----------|----------|-------------|-----------------|
| `Alsace_Basel_AF` | `BdD_Proto_Alsace` | Même zone, données complémentaires | commune + lieu_dit |
| `Alsace_Basel_AF` | `LoupBernard` | Chevauchement rive droite Rhin | coordonnées (~1km) |
| `Patriarche` | `ea_fr` | Même référentiel national | Code EA / NUMERO |
| `Patriarche` | `BdD_Proto_Alsace` | Même communes 67 | commune + EA |
| `necropoles_BFIIIb-HaD3` | `mobilier_sepult_def` | Nécropoles → sépultures | commune + lieu_dit |
| `necropoles_BFIIIb-HaD3` | `Inhumations silos` | Complémentarité BF III/Ha | commune + lieu_dit |
| `habitats-tombes riches` | `Alsace_Basel_AF` | Sites élites dans inventaire général | commune + type |
| `ADAB2011` | `Alsace_Basel_AF` | Zone Baden vs Alsace-Bâle | coordonnées (~1km) |
| `cag_68_texte` | `Alsace_Basel_AF` | CAG 68 sites ↔ inventaire digital | commune |

---

## 4. Complémentarité chronologique

| Phase | Sources principales | Sources complémentaires |
|-------|-------------------|------------------------|
| **Bronze Final III** (–1020/–800) | necropoles_BFIIIb-HaD3, Inhumations silos | mobilier_sepult_def |
| **Hallstatt ancien** (–800/–620) | necropoles_BFIIIb-HaD3, LoupBernard | mobilier_sepult_def, habitats-tombes riches |
| **Hallstatt final** (–620/–450) | LoupBernard, habitats-tombes riches | Alsace_Basel_AF, BdD_Proto_Alsace |
| **La Tène ancienne** (–450/–250) | LoupBernard, Alsace_Basel_AF | ADAB2011, BdD_Proto_Alsace |
| **La Tène finale** (–250/–25) | LoupBernard (oppida), Alsace_Basel_AF | ADAB2011 |
| **Multi/Indéterminé** | ADAB2011 (72% indét.), BdD_Proto_Alsace | Patriarche, BDD-fun_AFEAF24 |

---

## 5. Complémentarité typologique

| Type de site | Sources avec données riches |
|-------------|---------------------------|
| **OPPIDUM / ENCEINTE** | LoupBernard (90% enceintes), Alsace_Basel_AF, BdD_Proto_Alsace |
| **HABITAT** | ADAB2011, BdD_Proto_Alsace, ea_fr |
| **NECROPOLE / TUMULUS** | necropoles_BFIIIb-HaD3, mobilier_sepult_def, BDD-fun_AFEAF24 |
| **DEPOT** | ADAB2011, BdD_Proto_Alsace |
| **SANCTUAIRE** | rare — quelques occurrences dans BdD_Proto_Alsace |
| **Inhumation en silo** | Inhumations silos (unique) |
| **Sites d'élite** | habitats-tombes riches (unique — armement, or, char) |
| **Entités linéaires** | 2026_afeaf_lineaire (unique — voies, fossés) |

---

## 6. Matrice de correspondance des champs clés

| Champ BaseFerRhin | LoupBernard | ADAB2011 | Alsace_Basel | Proto_Alsace | Patriarche | necropoles | mobilier | Inhumations | ea_fr |
|---|---|---|---|---|---|---|---|---|---|
| `nom_site` | SITE_NAME | SITE_NAME | lieu_dit | lieu_dit | Nom_et_ou_adresse | Nom | lieu-dit | Site+Lieu dit | NOMUSUEL |
| `commune` | CITY_NAME | CITY_NAME | commune | commune | Nom_de_la_commune | Commune | Commune | Site | COMMUNE_PP |
| `type_site` | CARAC_LVL1 | CARAC_LVL1 | — | type_site | — | — | type sép | — | VESTIGES |
| `latitude` | LATITUDE | LATITUDE | y | — | — | Coord Y (L93) | Y(L93) | Y(L93) | — |
| `longitude` | LONGITUDE | LONGITUDE | x | — | — | Coord X (L93) | X(L93) | X(L93) | — |
| `date_debut` | STARTING_PERIOD | STARTING_PERIOD | — | (flags BA…LTCD) | — | Datation | — | — | — |
| `date_fin` | ENDING_PERIOD | ENDING_PERIOD | — | (flags BA…LTCD) | — | Datation | — | — | — |
| `source` | DATABASE_NAME | DATABASE_NAME | auteur | — | — | — | — | — | — |
| `ea_code` | — | — | — | EA | Code_national_de_l_EA | — | — | — | EA_NATCODE |

---

## 7. Stratégie de fusion recommandée

### Ordre de priorité d'ingestion

1. **`Alsace_Basel_AF`** — 1083 sites, coords, le plus complet pour la zone cible → socle géographique
2. **`LoupBernard_ArkeoGis`** — haute qualité, oppida/enceintes → enrichissement rive droite du Rhin
3. **`ADAB2011_ArkeoGis`** — couverture Nordbaden → extension Bade
4. **`BdD_Proto_Alsace`** — typologie riche → enrichissement des types de sites
5. **`Patriarche_ageFer`** + **`ea_fr`** — codes EA officiels → rattachement administratif
6. **`necropoles_BFIIIb-HaD3`** → couche funéraire avec chronologie fine
7. **`mobilier_sepult_def`** + **`Inhumations silos`** → données de détail (sépultures, individus)
8. **`habitats-tombes riches`** + **`BDD-fun_AFEAF24`** → enrichissement thématique
9. **`2026_afeaf_lineaire`** → entités linéaires (voies, fossés)
10. **`cag_68_texte`** → extraction textuelle CAG Haut-Rhin (parallèle au CAG 67)

### Principes de déduplication

- **Avec coordonnées** : distance < 500m + similarité toponymique > 0.7 → candidat doublon
- **Sans coordonnées** : commune + lieu_dit normalisé + période → clé composite
- **Codes EA** : jointure exacte sur `Code_national_de_l_EA` / `EA_NATCODE` entre Patriarche, ea_fr, BdD_Proto_Alsace
- **Priorité** : en cas de doublon, conserver la source avec le plus de champs remplis

### Architecture de données proposée

```
data/output/
├── sites.csv                    # Table principale : 1 ligne = 1 site
├── sepultures.csv               # Détail funéraire (lié à sites via site_id)
├── mobilier.csv                 # Mobilier par sépulture (lié à sepultures)
├── individus.csv                # Anthropologie (lié à sepultures)
├── sources.csv                  # Traçabilité source_id ↔ fichier_origine
└── dedup_log.csv                # Journal des fusions/doublons détectés
```

---

## 8. Estimation de couverture finale

En fusionnant les 15 sources, le projet BaseFerRhin devrait contenir :

| Métrique | Estimation |
|----------|-----------|
| Sites uniques (après dédup) | **2 500 – 3 500** |
| Sites avec coordonnées | **~1 800** (via Alsace_Basel_AF + ArkeoGIS + L93 → WGS84) |
| Sites avec chronologie | **~2 000** (via ArkeoGIS + necropoles + flags Proto_Alsace) |
| Sites avec code EA | **~900** (Patriarche + ea_fr + BdD_Proto_Alsace) |
| Couverture Bas-Rhin (67) | Bonne (Patriarche + CAG 67 sub-projet) |
| Couverture Haut-Rhin (68) | Moyenne → à compléter via CAG 68 |
| Couverture Bade-Wurtemberg | Bonne (LoupBernard + ADAB2011) |
| Couverture Bâle/Suisse | Partielle (Alsace_Basel_AF) |
