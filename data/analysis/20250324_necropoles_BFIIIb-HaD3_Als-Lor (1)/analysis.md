# Analyse — Nécropoles BF IIIb – Hallstatt D3 (Alsace-Lorraine)

## 1. Vue d'ensemble

| Élément | Détail |
|--------|--------|
| **Fichier** | `20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx` |
| **Chemin source** | `data/input/20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx` |
| **Format** | XLSX |
| **Volume** | **339 lignes**, **37 colonnes**, ~76 Ko |
| **Export métadonnées** | 2025-03-24 |
| **Contexte archéologique** | Inventaire de **nécropoles** et ensembles funéraires du **Bronze final IIIb** à **Hallstatt D3** en **Alsace et Lorraine** : transition **tumulus / tertre ↔ sépultures plates**, pratiques **inhumation / crémation**, indices d’**élitisme** (tombe à armes, architecture bois, textiles). Les colonnes détaillent des **étapes chronologiques** (Hallstatt B2-B3, C1, C2, D1, D2, D3 avec fourchettes calendaires) et des **marqueurs morphologiques** (tertre, tertre arasé, cercle funéraire, Langgraben). |

**Projet cible :** BaseFerRhin — déjà partiellement intégré dans `sites.csv` (traces de ce fichier en `source_references` pour certains sites).

---

## 2. Schéma des colonnes (colonnes clés)

### Identification et localisation

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Unnamed: 0` | int64 | 100 % | index ligne (1, 2, 3…) |
| `Région` | object | 100 % | Alsace, Lorraine |
| `Dept` | int64 | 100 % | 67, 68, 54 |
| `Commune` | object | 100 % | Altorf, Barr, Benfeld |
| `Nom` | object | ~95 % | Lange Stein, non localisé, Plateforme dép |
| `Date de fouille/découverte` | object | ~65,5 % | 2011-2014, 2018 |
| `localisation topographique` | object | ~55,2 % | placage lœss, graviers |

### Coordonnées

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Coordonnées x (Lambert 93)` | int64 | 100 % | 1034400, 1029876 |
| `Coordonnées y (Lambert 93)` | int64 | 100 % | 6834330, 6821099 |

*Note :* les statistiques min/max automatiques dans `metadata.json` peuvent inclure **valeurs aberrantes** (ex. Y très bas) — **valider** les plages L93 en contrôle qualité.

### Chronologie et occupation

| Colonne | Taux remplissage | Rôle |
|---------|------------------|------|
| `Occupation nécropole` | ~85 % | synthèse textuelle (Ha C - LT A, Bz D- Ha C-D1…) |
| `Datation` | ~86,1 % | Ha D, Ha C, Ha D1… |
| Colonnes binaires par phase (`Protohistoire ind`, `Hallstatt indéterminé`, `Etape 1…`, `Hallstatt B2-B3 (850-800)`, `Hallstatt C1 (800-660)`, …, `Hallstatt D3 (500-480)`) | variable | coches `-` / `1` / parfois `à vérifier` |

### Morphologie et pratiques funéraires

| Colonne | Rôle |
|---------|------|
| `Tertre (élévation)`, `Tertre arasé`, `cercle funéraire`, `Langgraben`, `Autre` | **tumulus** vs autres dispositifs |
| `Inhumation`, `crémation`, `pratique funéraire indéterminée` | comptages ou présence |
| `Présence textiles`, `signalisation/stèle`, `Architecture tombe/bois` | mobilier organique / architecture |
| `tombe élitaire`, `tombe à armes` | statut social |

### Documentation

| Colonne | Taux | Exemples |
|---------|------|----------|
| `Chronologie et commentaires` | ~90 % | notes détaillées sur phases et mobilier |
| `biblio` | ~98,5 % | clés biblio, références |

**Taux de remplissage moyen :** ~65,4 % — **confiance MEDIUM** (métadonnées).

**Anomalies :** `Unnamed: 0` = index ; colonne sans nom signalée.

---

## 3. Modèle de données (grain)

- **Une ligne = une nécropole** (ou un ensemble funéraire identifié comme tel), localisé par commune + nom de lieu + coordonnées.
- Plusieurs **phases** peuvent coexister sur un même site (colonnes étapes Hallstatt) : pour BaseFerRhin, cela correspond plutôt à **plusieurs phases** (`phase_id`) sous un même `site_id` — comme déjà modélisé dans `sites.csv`.

---

## 4. Qualité

| Aspect | Constat |
|--------|---------|
| **Coordonnées** | Toujours présentes en base ; contrôler **cohérence** avec la commune (outliers). |
| **Toponymes** | `Nom` parfois générique (« non localisé ») — réduit la qualité du `nom_site`. |
| **Chronologie** | Riche (sous-périodes + `Datation`) ; **Bronze final** présent (`Bz`, `Protohistoire`) — au-delà des bornes HALLSTATT seules du JSON. |
| **Binaire** | Mélange `-`, `1`, `oui`, nombres — normaliser en booléen / entier. |

---

## 5. Mapping vers BaseFerRhin

| Cible | Source |
|-------|--------|
| `nom_site` | `Nom` (filtrer « non localisé » → fallback `Commune` + commentaire) |
| `commune` | `Commune` | `toponymes_fr_de.json` |
| `pays` | `FR` (67, 68, 54) |
| `type_site` | **NECROPOLE** ; si tertre dominant → conserver NECROPOLE ou ajouter nuance **TUMULUS** selon règle (alias `tumulus`, `tertre`). |
| `x_l93`, `y_l93` | Colonnes Lambert 93 |
| `periode` / `sous_periode` | Croiser `Datation`, `Occupation nécropole`, colonnes de phase Hallstatt ; aligner Ha C, D1, D2, D3, LT A avec `periodes.json` |
| Phases multiples | Une ligne export **par phase** détectée (1 sur colonnes étape) ou période textuelle parsée — aligné sur modèle `phase_id` existant. |
| `source_references` | chemin fichier xlsx + `biblio` |

---

## 6. Stratégie d’ingestion

1. Charger le xlsx ; ignorer ou renommer `Unnamed: 0`.
2. Nettoyer binaires (`-` → 0, `1`/`oui` → 1).
3. Valider et corriger coordonnées aberrantes.
4. Parser chronologie multi-colonnes → liste de phases pour fusion avec `sites.csv`.
5. Déduplication forte avec **référentiel existant** (ce fichier a déjà alimenté des entrées).
6. Export schéma normalisé + log des mises à jour vs sites existants.

---

## 7. Limites

- **Précision** : points parfois **centroïdes** ou approximatifs ; `non localisé` malgré coordonnées.
- **Période** : BF IIIb et protohistoire — **hors** fenêtre stricte HALLSTATT/LA_TENE du seul `periodes.json` : prévoir libellés étendus ou `indéterminé`.
- **Redondance** : risque de **re-ingestion** si les mêmes lignes sont réimportées sans clé stable.
- **37 colonnes** : tout ne tient pas dans le schéma minimal ; préserver `Chronologie et commentaires` en annexe.

---

*Document basé sur `metadata.json` et `data/reference/`.*
