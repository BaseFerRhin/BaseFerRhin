# Analyse du jeu de données Patriarche — Entités archéologiques (âge du Fer)

**Fichier analysé :** `20250806_Patriarche_ageFer.xlsx`  
**Emplacement dans le dépôt :** `data/input/20250806_Patriarche_ageFer.xlsx` (copie de travail ; ce dossier `data/analysis/20250806_Patriarche_ageFer/` documente l’export).

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Source** | Base nationale **Patriarche** — entités archéologiques (EA) filtrées sur l’**âge du Fer** (export du 2025-08-06) |
| **Volume** | **836** lignes, **5** colonnes |
| **Grain** | **1 ligne = 1 EA** ; **`Code_national_de_l_EA`** unique sur les 836 enregistrements (**836** valeurs distinctes) |
| **Format** | XLSX (moteur typique : openpyxl / calamine), en-tête présente |
| **Référence spatiale** | **Aucune coordonnée** dans le fichier |
| **Emprise thématique** | France — inventaire centré sur le **Bas-Rhin (67)** (préfixe **`67`** dans `Numero_de_l_EA` et dans les chaînes d’identification) |
| **Chronologie** | Portée **proto- / âge du Fer** intégrée dans le libellé **`Identification_de_l_EA`** (ex. segments « Age du fer », « Age du bronze - Age du fer », etc.) — pas de champs datation numériques |
| **Typologie** | Indices **textuels** en fin de chaîne d’identification (ex. **fosse**, structures) — pas de colonne `type_site` normalisée |
| **Adresse / lieu précis** | **`Nom_et_ou_adresse`** renseigné pour **≈ 30,6 %** des lignes (**580** valeurs manquantes, **69,4 %**) |
| **Qualité globale** | **Élevée** sur les identifiants et l’identification textuelle ; **limitée** pour la **géolocalisation ponctuelle** (absence de XY) et pour l’**extraction automatique** de période / type sans NLP ou parsing de `Identification_de_l_EA` |

---

## 2. Schéma détaillé des colonnes

Types indiqués au sens logique (tel que décrit dans `metadata.json`). Taux de remplissage issus du même fichier.

| Colonne | Type logique | Remplissage | Valeurs uniques | Commentaire |
|---------|----------------|-------------|-----------------|-------------|
| `Code_national_de_l_EA` | entier | **100 %** | **836** | Identifiant national stable ; clé primaire logique |
| `Identification_de_l_EA` | texte | **100 %** | **836** | Chaîne structurée (numéro départemental, commune, micro-toponyme, **fourchette chronologique textuelle**, nature d’occupation / structure) |
| `Numero_de_l_EA` | texte | **100 %** | **836** | Numéro d’EA formaté (ex. `67 001 0006`) |
| `Nom_de_la_commune` | texte | **100 %** | **317** | Commune en majuscules (ex. ACHENHEIM) |
| `Nom_et_ou_adresse` | texte | **30,6 %** non nul | **234** | Complément d’adresse ou libellé ; beaucoup de valeurs manquantes ; échantillon inclut « Localisation inconnue », sigles type EHL/PDA |

**Taux de remplissage moyen (colonnes) :** **≈ 86,1 %** (pénalisé par `Nom_et_ou_adresse`).

---

## 3. Analyse du modèle de données

### 3.1 Grain et unicité

Le fichier est **plat** : pas de duplication de `Code_national_de_l_EA`. Chaque ligne correspond à une **entité archéologique** au sens Patriarche, potentiellement **plus fine** qu’un « site » synthétique BaseFerRhin (plusieurs EA peuvent relater le même ensemble géographique ou la même opération).

### 3.2 Information sémantique dans `Identification_de_l_EA`

La colonne **`Identification_de_l_EA`** condense plusieurs dimensions séparées par **`/`** (schéma récurrent dans les échantillons : numéro interne, code départemental, commune, lieu, **étiquette chronologique**, **type d’élément**). Pour l’ingestion vers BaseFerRhin, il faut soit :

- un **parseur déterministe** (regex + règles métier sur les segments), soit  
- une **extraction assistée** (NLP / table de motifs) pour remonter **période**, **type de vestige** et **micro-toponyme**.

### 3.3 Absence de géométrie

Sans coordonnées, le rattachement spatial repose sur **`Nom_de_la_commune`** (et éventuellement `Nom_et_ou_adresse`). La **précision** sera au mieux **communale** ou **adresse** après géocodage externe, avec un risque d’**homonymes** et de biais de centroïde.

### 3.4 Couverture départementale

Les numéros d’EA **`67 …`** et les libellés indiquent une sélection **Bas-Rhin** cohérente avec le périmètre Alsace du projet BaseFerRhin ; pour la fusion transfrontalière, croiser avec **`toponymes_fr_de.json`** pour l’affichage et les jointures de noms.

---

## 4. Analyse de qualité

| Critère | Constat |
|---------|---------|
| **Complétude des identifiants** | **Excellente** : pas de null sur les trois champs d’identification (`Code_national`, `Identification`, `Numero`) |
| **Complétude lieu précis** | **Faible** pour `Nom_et_ou_adresse` (**≈ 69 %** de valeurs manquantes) |
| **Doublons** | **Aucun** doublon de clé nationale sur les 836 lignes |
| **Cohérence spatiale** | Non vérifiable **in situ** (pas de XY) ; cohérence administrative à contrôler par référentiel communes |
| **Encodage** | XLSX — caractères accentués attendus dans les chaînes françaises |
| **Traçabilité source** | Forte via **code national** et **numéro EA** — idéal pour `identifiants_externes` |

**Niveau de confiance global (métadonnées) :** **HIGH** pour l’identification documentaire ; **géographiquement** dépendant d’un enrichissement postérieur.

---

## 5. Mapping vers le modèle BaseFerRhin

Références : `data/reference/types_sites.json`, `data/reference/periodes.json`, `data/reference/toponymes_fr_de.json`.

| Champ source | Cible BaseFerRhin (indicatif) | Transformation / remarques |
|--------------|------------------------------|-----------------------------|
| `Code_national_de_l_EA` | `identifiants_externes["patriarche_code_national"]` | Clé stable ; préfixer un `site_id` interne si agrégation multi-EA |
| `Numero_de_l_EA` | `identifiants_externes["patriarche_numero_ea"]` | Chaîne normalisée conservée telle quelle |
| `Identification_de_l_EA` | `description` / champs dérivés | Parser pour extraire **commune** (redondant), **lieu-dit**, **mentions chronologiques** (motifs `periodes.json`), **indices typologiques** (alignement `types_sites.json` : fosse → `HABITAT`, etc.) |
| `Nom_de_la_commune` | `commune` | Normaliser casse / accents pour jointure ; croiser `toponymes_fr_de.json` si besoin |
| `Nom_et_ou_adresse` | `adresse` / `commentaire_qualite` | Filtrer sentinelles (« Localisation inconnue ») ; alimenter géocodage si pertinent |
| — | `pays` | **`FR`** |
| — | `x_l93`, `y_l93` | **Géocodage** ou appariement à d’autres bases (ex. Alsace_Basel, BdD Proto) ; sinon NULL avec `precision_localisation` adaptée |
| (dérivé parsing) | `PhaseOccupation.periode` | Chevauchement avec fenêtres **HALLSTATT** / **LA_TENE** / **TRANSITION** selon `periodes.json` |
| (dérivé parsing) | `type_site` | Mapper « funéraire », « fosse », « enceinte », etc. vers enums du référentiel |

---

## 6. Stratégie d’ingestion (6 étapes)

1. **Chargement** — Lire la feuille XLSX, valider **5** colonnes et **836** lignes.  
2. **Nettoyage** — `str.strip()` sur textes ; normaliser commune ; marquer les adresses vides ou « inconnues ».  
3. **Parsing** — Extraire depuis `Identification_de_l_EA` les segments chronologiques et typologiques (règles + dictionnaire de motifs).  
4. **Classification** — Assigner `TypeSite` et `Periode` via `types_sites.json` et `periodes.json`.  
5. **Géoréférencement** — Jointure par commune / numéro EA avec d’autres jeux du dépôt, ou géocodage BAN/adresse ; documenter la méthode dans le rapport qualité.  
6. **Export** — CSV / GeoJSON / SQLite alignés sur le pipeline projet, avec traçabilité Patriarche.

---

## 7. Limites et précautions

- **Pas de coordonnées** : cartographie directe impossible ; risque de **chevauchement** de plusieurs EA sur une même carte sans appariement fin.  
- **Granularité EA** : une ligne n’est pas toujours un « site » unique au sens BaseFerRhin — prévoir **agrégation** ou **relations 1-n** site ↔ EA.  
- **Chronologie textuelle** : chaînes du type « Age du bronze - Age du fer » demandent une **politique de priorité** (phase dominante, multi-phase, ou `indéterminé`).  
- **Couverture** : échantillon métadonnées et intitulé du lot = **forte présence 67** ; vérifier l’absence d’autres départements si le fichier évolue.  
- **`Nom_et_ou_adresse` creux** : ne pas sur-interpréter l’absence d’adresse comme « lieu totalement inconnu » — l’info peut être dans **`Identification_de_l_EA`**.

---

*Document basé sur `data/analysis/20250806_Patriarche_ageFer/metadata.json` (avril 2026).*
