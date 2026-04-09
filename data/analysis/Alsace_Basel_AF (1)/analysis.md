# Analyse du jeu de données Alsace — Bâle (âge du Fer)

**Fichier analysé :** `Alsace_Basel_AF (1).xlsx`  
**Emplacement dans le dépôt :** `data/input/Alsace_Basel_AF (1).xlsx` (copie de travail ; ce dossier `data/analysis/Alsace_Basel_AF (1)/` documente l’export).

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Source** | Base de synthèse **Alsace — Bâle**, sites de l’**âge du Fer** (compilation régionale) |
| **Volume** | **1083** lignes, **16** colonnes |
| **Sites / grain** | **`id_site`** : **1070** valeurs distinctes pour **1083** lignes — **jusqu’à 3 lignes par `id_site`** (moyenne **≈ 1,01** ligne par id) : présence de **doublons partiels** ou versions multiples à traiter en agrégation |
| **Format** | XLSX, en-tête présente |
| **Référence spatiale** | Colonne **`epsg_coord`** : **deux systèmes** observés — **4326** (WGS84) et **25832** (ETRS89 / UTM zone 32N). Les champs **`x`** et **`y`** sont stockés en **texte** (`object`) : mélange **degrés décimaux** et **coordonnées projetées** selon la ligne |
| **Emprise** | **France** (départements Alsace), **Suisse** (ex. Bâle-Ville), **Allemagne** — **423** communes distinctes |
| **Chronologie** | **`decouverte_annee`** renseignée pour **≈ 83,2 %** des lignes (**182** manquantes) — il s’agit de l’**année de découverte / mention**, pas d’une datation archéologique du site |
| **Bibliographie** | **`ref_biblio`** **≈ 64,6 %** rempli ; **`ref_rapport`** **≈ 38,6 %** |
| **Métadonnée technique** | La colonne **`date`** (8 valeurs uniques, type datetime) correspond à des **dates d’édition / export du fichier** (2026), **pas** à la chronologie des sites — à **exclure** du mapping période archéologique |
| **Qualité globale** | **Élevée** pour la couverture régionale et la présence de coordonnées ; **attention critique** au **choix du SCR** ligne par ligne et à la **cohérence** des paires (x, y) |

---

## 2. Schéma détaillé des colonnes

| Colonne | Type (metadata) | Remplissage | Valeurs uniques | Commentaire |
|---------|-----------------|-------------|-----------------|-------------|
| `id_site` | int64 | **100 %** | **1070** | Identifiant interne de la base ; quelques id répétés (**max 3** lignes) |
| `pays` | texte | **100 %** | **3** | France, Suisse, Allemagne |
| `admin1` | texte | **93,1 %** | **5** | Bas-Rhin, Haut-Rhin, Bâle-Ville, etc. (**75** null, **6,9 %**) |
| `commune` | texte | **100 %** | **423** | |
| `lieu_dit` | texte | **98,0 %** | **915** | **22** null (**2,0 %**) |
| `lieu_dit_autre` | texte | **21,1 %** | **70** | Précision secondaire (ex. groupe nord/sud, Schlossberg) |
| `x` | texte | **99,5 %** | **996** | À parser en float ; interprétation dépend de **`epsg_coord`** |
| `y` | texte | **99,5 %** | **993** | Idem |
| `epsg_coord` | float64 | **99,3 %** | **2** | **4326.0** ou **25832.0** (**8** null) |
| `decouverte_annee` | texte | **83,2 %** | **237** | Année(s) de découverte / première mention |
| `decouverte_operation` | texte | **94,5 %** | **14** | ex. fouille, diagnostic, première mention bibliographique |
| `ref_biblio` | texte | **64,6 %** | **560** | |
| `ref_rapport` | texte | **38,6 %** | **224** | Chaînes parfois longues (séries d’années) |
| `auteur` | texte | **100 %** | **7** | Contributeurs de la fiche |
| `date` | datetime | **100 %** | **8** | **Métadonnée fichier** — ne pas utiliser comme datation site |
| `commentaire` | texte | **65,3 %** | **66** | Croisements communes, renvois à d’autres fiches |

**Taux de remplissage moyen :** **≈ 84,8 %**.

---

## 3. Analyse du modèle de données

### 3.1 Multi-lignes par `id_site`

Les **13** lignes « en trop » par rapport aux **1070** `id_site` uniques imposent une **étape d’agrégation** : comparer les doublons (coords, biblio, commentaires) et décider **fusion** ou **conservation de la ligne la plus complète**.

### 3.2 Systèmes de coordonnées

- **EPSG:4326** : `x` = longitude, `y` = latitude (ordre **x = lon, y = lat** cohérent avec les échantillons ~7,33 / 48,75).  
- **EPSG:25832** : coordonnées **métriques** UTM 32N ; conversion vers **WGS84** puis éventuellement **Lambert-93 (EPSG:2154)** pour le stockage BaseFerRhin.

Les statistiques min/max brutes dans `metadata.json` peuvent être **polluées** si des valeurs **mélangées** ont été agrégées sans filtre par EPSG — le contrôle **doit** être **par groupe `epsg_coord`**.

### 3.3 Couverture géographique du projet

Ce fichier est **au cœur** du périmètre BaseFerRhin (Alsace + Bâle + voisinage allemand). Le référentiel **`toponymes_fr_de.json`** soutient l’**harmonisation** des noms pour les jointures transfrontalières.

---

## 4. Analyse de qualité

| Critère | Constat |
|---------|---------|
| **Identifiant** | `id_site` quasi unique ; gérer explicitement les **répétitions** |
| **Coordonnées** | Forte disponibilité (**99,5 %**) mais **typage texte** et **double SCR** — risque d’**erreur** si l’on projette toutes les lignes comme WGS84 |
| **Cohérence EPSG ↔ valeurs** | Valider que pour **4326**, lon ∈ [-180,180] et lat ∈ [-90,90] ; pour **25832**, ordres de grandeur **centaines de milliers** de mètres |
| **Champ `date`** | **Ne pas confondre** avec chronologie archéologique |
| **Bibliographie** | Bonne couverture sur `ref_biblio` ; compléter avec `ref_rapport` quand présent |

**Niveau de confiance (métadonnées) :** **HIGH** sous réserve d’un **pipeline CRS ligne par ligne**.

---

## 5. Mapping vers le modèle BaseFerRhin

| Champ source | Cible | Remarques |
|--------------|-------|-----------|
| `id_site` | `identifiants_externes["alsace_basel_id_site"]` | Stable après agrégation |
| `pays`, `admin1`, `commune`, `lieu_dit` | `pays`, `region_admin`, `commune`, `nom_site` / `lieu_dit` | Aligner `pays` sur codes ISO si requis |
| `x`, `y`, `epsg_coord` | WGS84 puis `x_l93`, `y_l93` | Transformer selon EPSG ; `always_xy=True` |
| `decouverte_annee`, `decouverte_operation` | `Source` / métadonnée découverte | Pas substitution à `PhaseOccupation` sans autre source |
| `ref_biblio`, `ref_rapport` | `Source` (publications / rapports) | Dédupliquer après concaténation |
| `commentaire` | `description` / `commentaire_qualite` | |
| `auteur` | traçabilité ETL | |
| `date` (fichier) | métadonnée export | Exclure du modèle site |

Pour **`type_site`** et **`periode`**, ce fichier seul ne fournit pas toujours une typologie Fer explicite : enrichir par **jointure** avec Patriarche, BdD Proto, ou règles sur `commentaire`.

---

## 6. Stratégie d’ingestion (6 étapes)

1. **Chargement** — XLSX → DataFrame, 1083 × 16.  
2. **Nettoyage** — Parser `x`, `y` en float ; gérer `epsg_coord` null (ligne en `quality_report`).  
3. **Géodésie** — Par ligne : si 4326 → L93 ; si 25832 → WGS84 puis L93.  
4. **Agrégation** — Grouper par `id_site` ; fusionner biblio et commentaires ; résoudre conflits de coordonnées (priorité EPSG connu + cohérence).  
5. **Déduplication** — Vers `golden_sites.csv` et exports existants (distance + fuzzy).  
6. **Export** — CSV / GeoJSON avec `source` explicite.

---

## 7. Limites et précautions

- **Double projection** : erreur fréquente si l’on oublie **`epsg_coord`**.  
- **`decouverte_annee` ≠ datation** : ne pas remplir `datation_debut`/`fin` sans autres preuves.  
- **Doublons `id_site`** : risque de **sites dupliqués** en sortie sans agrégation.  
- **Emprise transnationale** : homogénéiser les noms (`toponymes_fr_de.json`) sans **forcer** des frontières administratives incorrectes.  
- **Métadonnées géographiques automatiques** dans `metadata.json` : les bornes globales min/max peuvent être **invalides** si le mélange CRS n’a pas été filtré — toujours **recalculer** après normalisation.

---

*Document basé sur `data/analysis/Alsace_Basel_AF (1)/metadata.json` (avril 2026).*
