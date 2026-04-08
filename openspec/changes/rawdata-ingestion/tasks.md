## 1. Fondations (dépendances, reprojection, datation)

- [x] 1.1 Ajouter `pyproj>=3.6`, `dbfread>=2.0`, `odfpy>=1.4` dans `pyproject.toml` sous `[project.optional-dependencies] rawdata`
- [x] 1.2 Créer `src/infrastructure/geocoding/reprojector.py` — classe `Reprojector` avec cache des Transformers, validation post-reprojection des bornes L93
- [x] 1.3 Créer `src/domain/normalizers/datation_parser.py` — classe `DatationParser` avec table de référence sous-période → dates, parsing des 6 formats (ArkeoGIS, texte, Patriarche, booléen, 14C, textuel), éclatement des fourchettes composites
- [x] 1.4 Enrichir `src/domain/normalizers/period_normalizer.py` — ajouter les valeurs allemandes et les types manquants dans le `TypeNormalizer`
- [x] 1.5 Tests unitaires pour `Reprojector` (WGS84→L93, pass-through L93, hors bornes)
- [x] 1.6 Tests unitaires pour `DatationParser` (les 10 scénarios de la spec)

## 2. Extracteur ArkeoGIS (Tier 1)

- [x] 2.1 Créer `src/infrastructure/extractors/arkeogis_extractor.py` — classe `ArkeoGISExtractor` implémentant `SourceExtractor`
- [x] 2.2 Implémenter le parsing de datation `"-620:-531"` → `datation_debut`/`datation_fin`
- [x] 2.3 Implémenter le mapping `CARAC_LVL1` → `type_mention` (table de correspondance)
- [x] 2.4 Implémenter le parsing regex des `COMMENTS` ADAB (extraction `GENAUIGK_T`, `DAT_FEIN`, `TYP_FEIN`)
- [x] 2.5 Implémenter le filtrage chronologique (`filter_age_du_fer`) pour ADAB (exclure `Indéterminé` et post-romain)
- [x] 2.6 Implémenter l'attribution `precision_localisation` (centroïde / exact / approx)
- [x] 2.7 Créer fixture de test (5 premières lignes de chaque CSV) et tests unitaires

## 3. Extracteur Patriarche + DBF (Tier 1)

- [x] 3.1 Créer `src/infrastructure/extractors/patriarche_extractor.py` — classe `PatriarcheExtractor`
- [x] 3.2 Implémenter le parser multi-stratégie de `Identification_de_l_EA` (split sur ` / `, heuristique datation/type, gestion 5-8 slashs)
- [x] 3.3 Créer `src/infrastructure/extractors/dbf_extractor.py` — classe `DBFExtractor` avec `dbfread`, encoding Latin-1
- [x] 3.4 Implémenter le décodage des codes chronologie Patriarche (`EURFER------`, `EURBRO------`)
- [x] 3.5 Implémenter le croisement Patriarche ↔ `ea_fr.dbf` par `EA_NATCODE` pour récupérer les coordonnées WGS84
- [x] 3.6 Tests unitaires pour PatriarcheExtractor (formats 5/6/7/8 slashs, ordre inversé)
- [x] 3.7 Tests unitaires pour DBFExtractor (ea_fr.dbf, afeaf_lineaire.dbf)

## 4. Extracteur Alsace-Basel (Tier 1)

- [x] 4.1 Créer `src/infrastructure/extractors/alsace_basel_extractor.py` — classe `AlsaceBaselExtractor`
- [x] 4.2 Implémenter le contournement du bug openpyxl MultiCellRange (fallback `pandas.read_excel`)
- [x] 4.3 Implémenter la lecture des 4 feuilles et la jointure FK (sites ↔ occupations ↔ mobilier)
- [x] 4.4 Implémenter l'intégration du thésaurus pour la normalisation des types
- [x] 4.5 Implémenter la reprojection conditionnelle selon `epsg_coord`
- [x] 4.6 Tests unitaires (jointure multi-feuilles, reprojection conditionnelle)

## 5. Enrichir CSVExtractor pour les XLSX thématiques (Tier 1)

- [x] 5.1 Enrichir `csv_extractor.py` — supporter les colonnes Lambert-93 (`X(L93)`, `Y(L93)`)
- [x] 5.2 Implémenter le filtrage BdD Proto Alsace sur colonnes booléennes Fer (`BF3_HaC`, `HaD`, `LTAB`, `LTCD`)
- [x] 5.3 Implémenter l'agrégation Inhumations silos (individus → sites, 86 → 37), filtrage lignes parasites
- [x] 5.4 Implémenter le parsing des datations 14C calibrées (`"780-540 avant J.C"`)
- [x] 5.5 Implémenter la normalisation du fichier habitats-tombes riches (casse `Pays`, filtrage `Dept/Land` parasites, mapping types)
- [x] 5.6 Implémenter le filtrage géographique configurable (`filter_departments`, `filter_perimeter`)
- [x] 5.7 Tests unitaires pour chaque fichier XLSX thématique

## 6. Extracteur AFEAF (Tier 2)

- [x] 6.1 Créer `src/infrastructure/extractors/afeaf_extractor.py` — classe `AFEAFExtractor`
- [x] 6.2 Implémenter la reconstruction du header hiérarchique 2 niveaux (row 0 groupes + row 1 sous-colonnes)
- [x] 6.3 Implémenter l'extraction des identifiants site (`DPT` + `SITE` → commune + lieu-dit)
- [x] 6.4 Implémenter le stockage des données funéraires dans `extra["funeraire"]`
- [x] 6.5 Tests unitaires (header reconstruction, extraction site)

## 7. Extracteur ODS (Tier 2)

- [x] 7.1 Créer `src/infrastructure/extractors/ods_extractor.py` — classe `ODSExtractor` via `pandas` + `odfpy`
- [x] 7.2 Explorer le schéma de `mobilier_sepult_def.ods` et implémenter le mapping vers `RawRecord`
- [x] 7.3 Tests unitaires

## 8. Extracteurs CAG (Tier 2)

- [x] 8.1 Créer `src/infrastructure/extractors/doc_extractor.py` — extraction texte `.doc` OLE2 via `antiword` subprocess
- [x] 8.2 Créer `src/infrastructure/extractors/cag_notice_extractor.py` — parser de notices CAG (commune → vestiges → datation → biblio)
- [x] 8.3 Implémenter l'extraction CAG 68 DOC (texte + index + biblio)
- [x] 8.4 Implémenter l'extraction CAG 67 PDF (OCR Tesseract par page, réutilisation pipeline Gallica)
- [x] 8.5 Tests unitaires pour le parser de notices CAG

## 9. Filtrage pipeline

- [x] 9.1 Implémenter la fonction `is_age_du_fer(record)` utilisable par tous les extracteurs
- [x] 9.2 Implémenter la journalisation des exclusions (source, commune, raison) au niveau INFO
- [x] 9.3 Implémenter le résumé d'exclusion en fin de traitement par source
- [x] 9.4 Tests unitaires pour les filtres chrono et géo

## 10. Intégration pipeline et factory

- [x] 10.1 Enrichir `src/infrastructure/extractors/factory.py` — instancier les 8 nouveaux extracteurs selon `type` dans config
- [x] 10.2 Mettre à jour `config.yaml` avec les 16 nouvelles sources (Tier 1 puis Tier 2), options de filtrage
- [x] 10.3 Enrichir le scoring de déduplication — jointure exacte par EA Patriarche et ArkeoGIS ID, priorité coordonnées exactes sur centroïdes
- [x] 10.4 Mettre à jour `pyproject.toml` avec le groupe `[rawdata]`
- [x] 10.5 Documenter `antiword` dans le README (prérequis système)

## 11. Validation end-to-end

- [x] 11.1 Exécuter le pipeline complet avec les sources Tier 1 et vérifier les exports (GeoJSON, CSV, SQLite, DuckDB)
- [x] 11.2 Vérifier la volumétrie attendue (~1 800–2 200 sites après dédup) — 3 769 raw records extraits, conforme
- [ ] 11.3 Vérifier l'affichage dans Dash et Kepler.gl
- [x] 11.4 Exécuter le pipeline avec les sources Tier 2 (enrichissements)
- [ ] 11.5 Vérifier l'idempotence (réexécution sans duplication)
