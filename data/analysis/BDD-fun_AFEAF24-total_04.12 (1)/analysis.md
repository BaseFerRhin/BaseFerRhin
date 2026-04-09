# Analyse du jeu de données AFEAF 2024 — Base funéraire (total 04.12)

**Fichier analysé :** `BDD-fun_AFEAF24-total_04.12 (1).xlsx`  
**Emplacement dans le dépôt :** `data/input/BDD-fun_AFEAF24-total_04.12 (1).xlsx` (copie de travail ; ce dossier `data/analysis/BDD-fun_AFEAF24-total_04.12 (1)/` documente l’export).

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Source** | **AFEAF** (Association Française pour l’Étude de l’Âge du Fer) — **base funéraire** consolidée (**version total au 04.12**, millésime 2024 dans le nom de fichier) |
| **Volume** | **401** lignes, **63** colonnes |
| **Grain** | **Non déterminé automatiquement** dans `metadata.json` — structure **multi-niveaux** : informations **SITE** (département, libellé de site, numéro de structure) et, sur les mêmes lignes, attributs **dépôt / individu** (NMI, type de dépôt, monument, fosse, mobilier, anthro, datation…) ; plusieurs lignes peuvent décrire **plusieurs sépultures ou individus** au sein d’un même site |
| **Format** | XLSX ; **en-tête composite** — mélange de **libellés explicites** (`info SITE`, `REMARQUES GENERALES`, `NMI / TYPE DEPOT`, blocs MONUMENT/FOSSE, etc.) et de **48 colonnes `Unnamed:`** dont le **sens** est porté par la **première ou les premières lignes** du tableau (effet « double ligne d’en-tête » ou tableau questionnaire) |
| **Référence spatiale** | **Pas de coordonnées** simples (X/Y) dans le schéma extrait ; localisation implicite par **`Unnamed: 1`** (libellé **SITE** : commune + précision) et **`info SITE`** (codes **département** 67, 68, libellé **DPT**) |
| **Emprise thématique** | **Alsace** et **collectivités voisines** couvertes par les départements **67** et **68** (échantillons métadonnées) — aligné avec le périmètre BaseFerRhin |
| **Contenu analytique** | Pratiques funéraires : **NMI** (nombre minimum d’individus), **types de dépôt** (simple/multiple, primaire/secondaire), **enclos fossoyés**, **tumulus**, dimensions et formes de fosses, **mobilier porté** et **dépôts d’offrande**, **réinterventions**, **modalités de dépôt**, **bio-démographie** (âge, sexe, genre mobilier), **datations** (mobilier, C14, phases relatives) |
| **Chronologie** | Colonne **`DATATION `** (nom avec espace terminal) : valeurs du type **Hallstatt D1**, **La Tène A**, etc. (**59** valeurs uniques sur le fichier) ; colonnes satellites **C14**, **phase chrono relative** avec remplissage plus faible |
| **Qualité globale** | **Taux de remplissage moyen élevé** (**≈ 96,7 %** au niveau cellules) ; **issue** documentée : **48 colonnes sans nom** — nécessité d’une **phase de reconstruction de schéma** avant toute ingestion robuste |

---

## 2. Schéma détaillé des colonnes

Le fichier combine **colonnes nommées** et **`Unnamed: N`**. Les **échantillons** dans `metadata.json` montrent que la **ligne 1** (ou les premières lignes) joue souvent le rôle de **sous-en-tête** (ex. « NMI », « Type dépôt 1 », « ENCLOS FOSSOYE »).

**Bloc identification site (début de tableau)**  
| Colonne | Remplissage | Uniques | Rôle |
|---------|-------------|---------|------|
| `info SITE` | **100 %** | **5** | Code **DPT** ou valeur « DPT » / numéros **67**, **68** |
| `Unnamed: 1` | **100 %** | **21** | Libellé **SITE** (ex. « Colmar rue des Aunes ») — **attention** : peu de modalités uniques = mélange **étiquettes** et **données** |
| `Unnamed: 2` | **99,0 %** | **383** | Numéro de structure **N° ST** |
| `REMARQUES GENERALES` | **67,3 %** | **83** | Notes générales (dendro, tertre, etc.) |

**Bloc dépôt / individu (extrait)**  
- `NMI / TYPE DEPOT`, `Unnamed: 5`…`Unnamed: 7` : types de dépôt, NMI, numéro d’individu.  
- `MONUMENT (enclos fossoyé)` … `MONUMENT (tumulus avéré)` : présence / forme / dimensions enclos et tumulus.  
- `FOSSE` et colonnes suivantes : morphologie et dimensions de fosse.  
- Blocs **AMENAGEMENT**, **MOBILIER ASSOCIÉ**, **DÉPÔTS d'OFFRANDE**, **REINTERVENTIONS**, **MODALITE DEPÔT**, **BIO**, **DATATION** (colonne source avec espace terminal dans le fichier), **OBSERVATIONS DIVERSES**.

**Colonnes les moins remplies (extrait metadata)**  
- `OBSERVATIONS DIVERSES` : **≈ 42,1 %** renseigné.  
- `Unnamed: 59`, `Unnamed: 60`, `Unnamed: 61` (C14 / phases) : **≈ 13,5 %** à **17,5 %** de nulls.

---

## 3. Analyse du modèle de données

### 3.1 Structure « questionnaire » AFEAF

Le modèle ressemble à une **grille de saisie** où :

- les **colonnes regroupées** décrivent des **dimensions** (monument, fosse, offrandes, position du corps…) ;  
- les valeurs **`oui` / `non` / `indéterminé` / `*`** sont fréquentes ;  
- le **`NMI`** et le **numéro d’individu** permettent de distinguer **plusieurs dépôts** sur un même site.

Pour BaseFerRhin, il faut décider si l’on ingère au **niveau site** (agrégat), **niveau sépulture** (N° ST), ou **niveau individu** — le fichier permet théoriquement les trois avec des règles d’agrégation.

### 3.2 Identification du site

Le couple (**`info SITE`**, **`Unnamed: 1`**) matérialise le **contexte géo-administratif** et le **nom d’usage** du site. **`Unnamed: 2`** (`N° ST`) distingue les **structures** au sein d’un même site.

### 3.3 Datation

La colonne **`DATATION `** et les champs **C14** supportent le mapping vers **`periodes.json`** (Hallstatt / La Tène) et les **sous-périodes** (Ha D1, LT A…). Les formats mélangent **libellés français**, **intervalles calibrés** (ex. « 801-550 BC ») et **BP**.

---

## 4. Analyse de qualité

| Critère | Constat |
|---------|---------|
| **Schéma** | **48 colonnes `Unnamed`** — risque d’**erreur sémantique** sans reconstruction d’en-têtes |
| **Complétude globale** | **Élevée** sur le corps du tableau |
| **Cohérence** | Valeurs **`*`** = souvent « non concerné » — à traiter comme **NULL** métier |
| **Granularité** | **Hétérogène** — comparaisons de NMI entre sites exigent une **normalisation** du nombre de lignes par site |
| **Géographie** | Pas de coordonnées ; **géocodage** ou jointure externe requise |

**Niveau de confiance (métadonnées) :** **HIGH** sur la richesse du contenu funéraire ; **modéré** sur l’**automatisme** sans étape de **profilage** des premières lignes.

---

## 5. Mapping vers le modèle BaseFerRhin

| Concept AFEAF | Cible BaseFerRhin | Remarques |
|---------------|------------------|-----------|
| Site (`Unnamed: 1` + DPT) | `Site` : `commune` / `nom_site` (parser le libellé) | Extraire commune si pattern stable |
| N° ST | `identifiants_externes["afeaf_numero_structure"]` ou sous-entité sépulture | |
| NMI | attribut démographique / `description` | Agrégation site : max ou somme selon règle |
| Enclos / Tumulus / Fosse | `type_site` → `NECROPOLE`, `TUMULUS`, nuances | `types_sites.json` (tumulus, enclos funéraire) |
| Types de dépôt | `description` / tags | |
| Mobilier, offrandes | `PhaseOccupation.mobilier_associe` ou équivalent | Liste de tags |
| `DATATION `, C14 | `PhaseOccupation` : `periode`, `sous_periode`, bornes si parsées | |
| REMARQUES, OBSERVATIONS | `commentaire_qualite` | |

---

## 6. Stratégie d’ingestion (6 étapes)

1. **Profilage** — Lire les **10–20 premières lignes** brutes pour reconstruire la **vraie** ligne d’en-tête (fusion ligne 0 + ligne 1).  
2. **Renommage** — Remplacer les `Unnamed` par des noms stables (slug) dérivés des libellés fusionnés.  
3. **Filtrage** — Écarter les lignes entièrement « métadonnées de grille » (ex. répétitions de « DPT », « SITE ») si présentes.  
4. **Normalisation** — Mapper `oui`/`non`/`*`/vides vers booléens et NULL.  
5. **Agrégation** — Produire une couche **site** et optionnellement **structure** (N° ST).  
6. **Jointure spatiale** — Avec Alsace_Basel_AF / géocodage ; export CSV + GeoJSON si coords obtenues.

---

## 7. Limites et précautions

- **Schéma fragile** : toute **mise à jour AFEAF** peut décaler colonnes — tests de régression sur les en-têtes.  
- **Pas d’ID site explicite** dans les métadonnées : construire un **`site_key`** déterministe (hash normalisé du libellé + DPT) ou laisser l’appariement manuel pour les homonymes.  
- **NMI et multi-lignes** : risque de **double comptage** si l’on somme sans regroupement par site.  
- **Sépulture vs site** : BaseFerRhin orienté « site » — documenter si les fiches restent **funéraires agrégées** ou **détaillées**.  
- **Données sensibles** : données bio-démographiques — respecter les **politiques de publication** du projet.

---

*Document basé sur `data/analysis/BDD-fun_AFEAF24-total_04.12 (1)/metadata.json` (avril 2026).*
