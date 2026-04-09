# Analyse du jeu de données BdD Proto — Alsace

**Fichier analysé :** `BdD_Proto_Alsace (1).xlsx`  
**Emplacement dans le dépôt :** `data/input/BdD_Proto_Alsace (1).xlsx` (copie de travail ; ce dossier `data/analysis/BdD_Proto_Alsace (1)/` documente l’export).

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Source** | **Base de données Protohistoire Alsace** — inventaire régional multi-périodes avec focus documentaire sur le **second millénaire** et transitions vers l’âge du Fer |
| **Volume** | **1127** lignes, **23** colonnes |
| **Grain** | **1 ligne = 1 enregistrement** ; clé **`id`** : **1127** valeurs uniques (**1,0** ligne par id en moyenne) |
| **Format** | XLSX, en-tête présente |
| **Référence spatiale** | **Aucune coordonnée** dans le fichier |
| **Emprise** | **Alsace** (communes françaises) — **340** communes distinctes |
| **Typologie** | Colonne **`type_site`** : **7** modalités (échantillons : **habitat**, **funéraire**, **mobilier**…) — **3** lignes sans `type_site` (**0,3 %** null) |
| **Chronologie** | **`datation_1`** toujours renseignée (**100 %**) — libellés larges (Bronze, Néolithique final, transitions « Bronze final/Hallstatt », etc.) ; **`datation_2`** **≈ 42,1 %** rempli (précision type « Bze C-D », « Ha D1 », « LT… ») |
| **Indicateurs binaires de période** | Colonnes **`BA`**, **`BM`**, **`BF1`**, **`BF2`**, **`BF3_HaC`**, **`HaD`**, **`LTAB`**, **`LTCD`** : flags **0/1** (float) avec **fortes proportions de null** — servent de **filtres thématiques** plutôt que de datation continue |
| **Colonnes vides** | **`type_precision`** et **`conservati`** : **100 %** null — inutiles pour l’ingestion sans autre source |
| **Qualité globale (métadonnées)** | **Confiance LOW** ; **taux de remplissage moyen** des colonnes **≈ 41,5 %** — jeu **riche sémantiquement** sur le registre proto- mais **hétérogène** ; **indispensable** pour l’Alsace malgré les lacunes |

---

## 2. Schéma détaillé des colonnes

| Colonne | Remplissage | Uniques | Rôle principal |
|---------|-------------|---------|----------------|
| `id` | **100 %** | **1127** | Clé primaire logique |
| `commune` | **100 %** | **340** | Localisation administrative |
| `lieu_dit` | **97,6 %** | **762** | Micro-toponyme / chantier |
| `EA` | **11,4 %** | **48** | Lien possible vers numéro EA (souvent vide) |
| `oa` | **42,6 %** | — | Identifiant opération / dossier |
| `type_oa` | **57,1 %** | **7** | fouille, diagnostic, découverte isolée, etc. |
| `annee_dec` | **55,1 %** | **103** | Année(s) de découverte / opération (texte, parfois plage) |
| `type_site` | **99,7 %** | **7** | habitat, funéraire, mobilier, … |
| `type_precision` | **0 %** | 0 | Colonne vide |
| `structures` | **53,4 %** | **135** | Description de structures |
| `conservati` | **0 %** | 0 | Colonne vide |
| `datation_1` | **100 %** | **32** | Grande période |
| `datation_2` | **42,1 %** | **40** | Affinement typo-chrono |
| `rq` | **41,7 %** | **142** | Remarques quantitatives / fouille |
| `biblio` | **56,2 %** | **341** | Bibliographie |
| `BA` … `LTCD` | **5,8 %** à **18,9 %** selon colonne | — | Présence / attribution période (flags) |

---

## 3. Analyse du modèle de données

### 3.1 Cœur « site » sans géométrie

Chaque ligne décrit un **ensemble protohistorique** localisé par **commune** et souvent **lieu-dit**. Sans XY, le lien spatial au modèle BaseFerRhin repose sur **appariement** avec des jeux coordonnés (ex. **Alsace_Basel_AF**) ou sur géocodage.

### 3.2 `type_site` et BaseFerRhin

Les valeurs **habitat**, **funéraire**, **mobilier** se mappent vers `types_sites.json` :

- **funéraire** → **`NECROPOLE`** / **`TUMULUS`** selon `structures` / `datation_2` ;  
- **habitat** → **`HABITAT`** (ou **`OPPIDUM`** si indices d’enceinte dans `structures` / `rq`) ;  
- **mobilier** → souvent **`DEPOT`** ou **`HABITAT`** selon contexte (`type_oa`, `rq`).

### 3.3 Chronologie : `datation_1` + `datation_2` + flags

- **`datation_1`** positionne souvent le **Bronze** ou des **chevauchements** ; pour BaseFerRhin (Fer), filtrer les lignes où **`LTAB`**, **`LTCD`**, **`HaD`**, **`BF3_HaC`**, ou les textes **`datation_*`** indiquent une **composante Hallstatt / La Tène**.  
- **`datation_2`** fournit des **codes proches** des sous-périodes de `periodes.json` (Ha D1, LT A, etc.) — utile pour `sous_periode`.

### 3.4 Lien Patriarche / EA

Le champ **`EA`** est **≈ 88,6 %** vide : lorsqu’il est présent, il peut servir de **pont** vers **`Numero_de_l_EA`** / codes Patriarche après normalisation des formats.

---

## 4. Analyse de qualité

| Critère | Constat |
|---------|---------|
| **Unicité** | **1127** `id` uniques — pas de doublon de clé |
| **Colonnes mortes** | **`type_precision`**, **`conservati`** — signalées dans `metadata.json` |
| **Complétude** | **Faible en moyenne** ; champs critiques (`biblio`, `structures`, `annee_dec`) partiels |
| **Cohérence** | Lecture humaine recommandée pour **`type_site` = mobilier`** (ambiguïté dépôt vs site) |
| **Spatiale** | Absence totale de coordonnées |

---

## 5. Mapping vers le modèle BaseFerRhin

| Champ source | Cible | Remarques |
|--------------|-------|-----------|
| `id` | `identifiants_externes["bdd_proto_alsace_id"]` | |
| `commune`, `lieu_dit` | `commune`, `nom_site` | `toponymes_fr_de.json` pour affichage |
| `type_site`, `structures`, `rq` | `type_site` (enum) | Règles de désambiguïsation |
| `datation_1`, `datation_2` | `PhaseOccupation` | Parser texte + flags ; chevaucher `periodes.json` |
| `annee_dec` | métadonnée découverte | |
| `type_oa` | `statut_fouille` / commentaire | fouille → fouille ; diagnostic → prospection ; etc. |
| `biblio` | `Source` | |
| `EA`, `oa` | `identifiants_externes` | Jointure Patriarche / SRA |
| Flags `BA`…`LTCD` | filtres d’inclusion Fer | Exporter ou filtrer les non-Fer selon politique projet |

---

## 6. Stratégie d’ingestion (6 étapes)

1. **Chargement** — 1127 × 23.  
2. **Filtrage optionnel** — Restreindre aux enregistrements **âge du Fer** (flags + motifs `datation_*`).  
3. **Normalisation** — Typologie et périodes via référentiels JSON.  
4. **Appariement spatial** — Merge fuzzy / EA avec Alsace_Basel_AF ou Patriarche.  
5. **Déduplication** — Vers autres exports BaseFerRhin.  
6. **Export** — CSV avec traçabilité `bdd_proto_alsace`.

---

## 7. Limites et précautions

- **Multi-périodes** : beaucoup d’entrées **Bronze** — ne pas les importer comme Fer sans critère explicite.  
- **Pas de XY** : même limite que Patriarche pour la carte fine.  
- **Flags creux** : ne pas sur-interpréter un **1** isolé sans lecture du texte.  
- **Colonnes vides** : ignorer ou supprimer du schéma cible.  
- **`mobilier` comme `type_site`** : risque de confusion avec **dépôt métallique** vs **mobilier de structure** — utiliser `structures` et `type_oa`.

---

*Document basé sur `data/analysis/BdD_Proto_Alsace (1)/metadata.json` (avril 2026).*
