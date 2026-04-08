## Context

Le projet BaseFerRhin est une base de données archéologique de l'âge du Fer du Rhin supérieur. Le pipeline ETL existant (8 étapes `DISCOVER → EXPORT`) utilise une architecture Clean (domain / infrastructure / application) avec des modèles Pydantic (`Site`, `PhaseOccupation`, `Source`, `RawRecord`), des extracteurs pluggables via un `SourceExtractor` Protocol, et un multi-géocodeur (BAN, Nominatim, GeoAdmin). Les coordonnées internes sont en Lambert-93 (EPSG:2154).

Le corpus `RawData/` contient 16 fichiers hétérogènes (CSV, XLSX, ODS, DBF, DOC OLE2, PDF scan) provenant de bases professionnelles (ArkeoGIS, Patriarche, AFEAF, CAG). Le modèle `PhaseOccupation` valide les sous-périodes contre un ensemble fermé `_VALID_SUB_PERIODS` qui n'accepte que des valeurs simples (`Ha C`, `Ha D`, `LT A`…).

## Goals / Non-Goals

**Goals:**
- Ingérer les 16 fichiers bruts en produisant des `RawRecord` normalisés via le pipeline existant
- Atteindre ~1 800–2 200 sites après déduplication (contre 20 actuellement)
- Préserver la compatibilité avec le modèle Pydantic existant (pas de modification de `_VALID_SUB_PERIODS`)
- Rendre le filtrage chronologique/géographique configurable sans modification de code
- Maintenir la traçabilité source → site pour chaque enregistrement ingéré

**Non-Goals:**
- Modifier le modèle de domaine Pydantic (Site, PhaseOccupation, Source, enums)
- Créer une UI spécifique pour l'exploration des données brutes
- Traiter les données ostéologiques individuelles (Inhumations silos) comme un modèle de premier niveau
- Atteindre une couverture OCR parfaite sur le PDF CAG 67 (209 MB)
- Ingérer des sources hors périmètre Rhin supérieur (Lorraine, Rhénanie)

## Decisions

### D1 — Éclater les fourchettes chronologiques plutôt qu'étendre le modèle

**Choix** : `"Ha C-D"` produit 2 `PhaseOccupation` distinctes (`Ha C` + `Ha D`) plutôt qu'ajouter `"Ha C-D"` à `_VALID_SUB_PERIODS`.

**Alternatives considérées** :
- *Étendre `_VALID_SUB_PERIODS`* : contaminerait le modèle avec des valeurs composites non-standard, rendrait les requêtes par sous-période ambiguës
- *Stocker en texte libre* : perdrait la validation Pydantic

**Rationale** : l'éclatement préserve l'intégrité du modèle, simplifie les requêtes (`WHERE sous_periode = 'Ha D'`), et n'ajoute qu'une indirection au parsing. Les bornes `datation_debut`/`datation_fin` couvrent la fourchette complète sur chaque phase.

### D2 — Extracteurs spécialisés plutôt que CSVExtractor générique surchargé

**Choix** : créer `ArkeoGISExtractor`, `PatriarcheExtractor`, `AlsaceBaselExtractor`, `AFEAFExtractor` comme classes distinctes implémentant `SourceExtractor`.

**Alternatives considérées** :
- *Enrichir CSVExtractor avec des hooks/callbacks* : trop complexe, violerait le SRP, le CSVExtractor deviendrait un god-class
- *Extracteur générique avec configuration YAML* : insuffisant pour les cas complexes (Patriarche multi-stratégie, AFEAF header hiérarchique, Alsace-Basel jointures)

**Rationale** : chaque source a une logique métier spécifique (parsing datation ArkeoGIS, éclatement slashs Patriarche, jointure FK Alsace-Basel). Des extracteurs dédiés sont plus testables, lisibles et maintenables.

### D3 — `antiword` CLI plutôt que bibliothèque Python pour les .doc OLE2

**Choix** : pré-extraction texte via `antiword` en subprocess, puis parsing du texte brut.

**Alternatives considérées** :
- *`python-docx`* : ne supporte **pas** le format OLE2, uniquement Open XML (.docx)
- *`textract`* : wrapper lourd avec dépendances système multiples
- *`olefile`* : lecture bas niveau OLE2 nécessitant un parser Word Document complet

**Rationale** : `antiword` est léger, fiable, packagé dans tous les gestionnaires de paquets (`brew`, `apt`), et produit du texte brut structuré prêt pour le parsing de notices CAG.

### D4 — Filtrage dans l'extracteur plutôt qu'étape pipeline séparée

**Choix** : chaque extracteur applique un filtre `is_age_du_fer()` et journalise les exclusions. Une option `filter_age_du_fer: true` dans `config.yaml` active le filtrage.

**Alternatives considérées** :
- *Étape FILTER dans le pipeline* : ajouterait de la complexité au pipeline, les données exclues occuperaient de l'espace disque en checkpoint intermédiaire
- *Post-filtrage lors de l'export* : toute la chaîne normalisation+géocodage serait exécutée sur des données inutiles

**Rationale** : filtrer tôt réduit le volume traité par les étapes coûteuses (géocodage, déduplication). La journalisation garantit la traçabilité.

### D5 — `pyproj` pour la reprojection plutôt que formules manuelles

**Choix** : utiliser `pyproj.Transformer` avec un cache des transformers par EPSG source.

**Alternatives considérées** :
- *Formules de reprojection manuelles* : fragile, erreur-prone pour les projections complexes (L93 = projection conique conforme)
- *`geopandas`* : dépendance lourde (GDAL/GEOS) pour un besoin ponctuel de reprojection

**Rationale** : `pyproj` est la référence Python pour les transformations de coordonnées, léger (pas de dépendance GDAL), et déjà utilisé implicitement par l'écosystème géospatial.

### D6 — Prioritisation en 2 tiers

**Choix** : traiter d'abord les sources primaires (sites + coordonnées + identifiants), puis les enrichissements (mobilier, ostéologie, contexte funéraire).

**Rationale** : les fichiers Tier 1 produisent des sites nouveaux avec identifiants de jointure (EA Patriarche, ArkeoGIS ID). Les fichiers Tier 2 enrichissent ces sites sans en créer de nouveaux. Traiter le Tier 1 d'abord maximise le ROI et permet de valider la déduplication avant d'ajouter du détail.

## Risks / Trade-offs

- **[Qualité spatiale LoupBernard]** 100% des 116 sites sont des centroïdes de communes → les points sur la carte seront regroupés au centre des villes, pas sur les sites réels. → *Mitigation* : marquer `precision_localisation=centroïde`, afficher visuellement dans l'UI.

- **[Volume ADAB post-filtrage]** Seulement ~130/656 sites ont une datation âge du Fer exploitable. Le ROI de cet extracteur est modéré. → *Mitigation* : l'extracteur est simple (même format ArkeoGIS), le coût de développement est faible.

- **[Bug openpyxl Alsace-Basel]** Le fichier `Alsace_Basel_AF` plante openpyxl sur les data validations (`MultiCellRange` error). → *Mitigation* : utiliser `pandas.read_excel()` qui ignore ces validations, ou pré-convertir via LibreOffice CLI.

- **[Variabilité format Patriarche]** L'ordre datation/type dans `Identification_de_l_EA` est variable (5-8 slashs). → *Mitigation* : parser multi-stratégie avec heuristiques (mots-clés datation vs type). Tests sur les 836 lignes réelles.

- **[OCR CAG 67]** Le PDF de 209 MB est un scan ancien. Le taux d'erreur OCR sera élevé. → *Mitigation* : priorité basse (Tier 2). Ne traiter que si les résultats Tier 1 sont satisfaisants. Fallback : extraction manuelle des sites principaux.

- **[Dépendance système antiword]** `antiword` doit être installé séparément. → *Mitigation* : documenter dans le README, vérifier la disponibilité au démarrage de l'extracteur, message d'erreur explicite.

- **[Déduplication inter-sources]** Avec ~3 750 sites bruts provenant de 16 sources, le taux de doublons sera élevé. La qualité du merge dépend de la précision du géocodage. → *Mitigation* : prioriser la jointure exacte par identifiant EA avant le scoring fuzzy. Seuils de dédup configurables.
