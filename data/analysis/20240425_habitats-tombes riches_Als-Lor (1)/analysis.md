# Analyse — Habitats et tombes riches (Alsace-Lorraine)

## 1. Vue d'ensemble

| Élément | Détail |
|--------|--------|
| **Fichier** | `20240425_habitats-tombes riches_Als-Lor (1).xlsx` |
| **Chemin source** | `data/input/20240425_habitats-tombes riches_Als-Lor (1).xlsx` |
| **Format** | XLSX |
| **Volume** | **110 lignes**, **21 colonnes**, ~22 Ko |
| **Export métadonnées** | 2024-04-25 |
| **Contexte archéologique** | Recensement de **sites d’élite** : **tombes riches** (armement, or, chars, importations de récipients) et **habitats / fortifications de hauteur** en **Alsace-Lorraine** et marges allemandes (Bade-Wurtemberg, Rhénanie-Palatinat). Chronologie centrée **Hallstatt / La Tène** (Hiérarchisation sociale, princier / aristocratique). |

**Particularité majeure :** **aucune coordonnée** dans le fichier — géolocalisation uniquement par toponymie (commune, lieudit).

**Projet cible :** BaseFerRhin.

---

## 2. Schéma des colonnes (colonnes clés)

### Localisation administrative

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Pays` | object | ~97,3 % | D, F, f (à normaliser DE/FR) |
| `Dept/Land` | object | ~99,1 % | Bade-Wurtemberg, Rhénanie-Palatinat, `54` |
| `Commune` | object | ~97,3 % | Breisach-am-Rhein, Hügelsheim, Ihringen |
| `Lieudit` | object | ~92,7 % | Gündlingen, Münsterberg |

### Nature du site et mobilier

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `type` | object | ~97,3 % | tombe riche, site fortifié de hauteur, tombe princière |
| `armement` | object | ~54,5 % | tombe à char, tombe à épée… |
| `Unnamed: 6` | object | ~13,6 % | Mors, harnachement, lance (colonne mal nommée) |
| `or` | object | ~36,4 % | torque, bracelet, boucles d’oreilles… |
| `Corail` | object | ~10 % | oui, perles |
| `oenochoé/Olpé/Stamnoï, etc.` | object | ~7,3 % | Schnabelkanne, récipients |
| `parure/accessoires` | object | ~26,4 % | fibules, bracelets… |
| `Chaudron`, `bassin`, `situle/ciste` | object | faible | mobilier banquetique |
| `présence textile`, `verre`, `Céramique`, `Autre` | object | variable | traces textiles, perles, céramique, ambre… |

### Chronologie et notes

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Datation` | object | ~97,3 % | Hallstatt C1, Hallstatt D3-LT A, Ha D3 |
| `Datation globale Tum` | object | ~17,3 % | Hallstatt C-LTA, Hallstatt D2/D3 |
| `Remarques` | object | ~69,1 % | datation par fibule, références biblio |

**Taux de remplissage moyen (toutes colonnes) :** ~41,2 % — mobilier très **hétérogène** selon les entrées.

**Anomalies :** colonne **`Unnamed: 6`** (86,4 % vide) — renommer manuellement après inspection (souvent complément armement / harnachement).

---

## 3. Modèle de données (grain)

- **Une ligne = un enregistrement « site ou sépulture d’élite »** (tombe riche isolée, tumulus princier, oppidum ou site fortifié de hauteur).
- Pas d’ID explicite dans les métadonnées ; unicité à reconstruire par **`Commune` + `Lieudit` + `type` + `Datation`** (fragile).
- **Pas de sous-découpage** intra-site (nombre de tombes) sauf si porté dans `Remarques`.

---

## 4. Qualité

| Aspect | Constat |
|--------|---------|
| **Coordonnées** | **Aucune** — `geographic` vide dans `metadata.json`. Géoréférencement postérieur (API adresse, fonds ArkeoGIS, littérature) nécessaire pour carte. |
| **Pays / Dept** | Codes hétérogènes (`D`, `F`, `f`) et libellés allemands ; homogénéisation requise. |
| **Chronologie** | `Datation` bien renseignée ; formulations « Hallstatt », « Ha », « LT » compatibles avec `periodes.json`. |
| **Confiance** | `confidence_level`: **LOW** ; issue : **Unnamed: 6**. |

---

## 5. Mapping vers BaseFerRhin

| Cible | Source | Remarques |
|-------|--------|-----------|
| `nom_site` | `Lieudit` ou combinaison `Commune` — `Lieudit` | Si lieudit vide, utiliser `Commune` + précision `type`. |
| `commune` | `Commune` | Normaliser avec `toponymes_fr_de.json` (ex. Breisach am Rhein). |
| `pays` | `Pays` + `Dept/Land` | D → DE, F/f → FR ; BW/RP → DE. |
| `type_site` | `type` | « site fortifié de hauteur » → **OPPIDUM** ; « tombe riche / princière » → **NECROPOLE** ou **TUMULUS** selon contexte (alias `tumulus`, `tombe à char`). |
| `x_l93`, `y_l93` | *Absents* | Laisser vides ou compléter par **géocodage externe** ; ne pas inventer. |
| `periode` / `sous_periode` | `Datation`, `Datation globale Tum` | Parser Hallstatt / La Tène et sous-phases. |
| Richesse mobilier | Colonnes armement, or, char (dans texte) | Métadonnées étendues ou champ `notes` / table annexe. |

---

## 6. Stratégie d’ingestion

1. **Chargement** Excel avec `openpyxl`.
2. **Normalisation** pays, départements, casses (`f` → `F`).
3. **Renommage** `Unnamed: 6` après analyse manuelle ou première ligne non vide.
4. **Classification** `type_site` via `types_sites.json` (oppidum, nécropole, tumulus).
5. **Chronologie** : règles sur `Datation` + fichier `periodes.json`.
6. **Géocodage optionnel** : hors périmètre du seul fichier — tracer `geocode_status`.
7. **Déduplication** avec `sites.csv` sur **nom + commune + pays** (sans distance, faute de coords).
8. **Export** schéma normalisé ; coordonnées vides acceptées avec flag.

---

## 7. Limites

- **Aucune précision spatiale** dans la source : risque d’**homonymes** et d’**erreurs de géocodage**.
- **Couverture** : elite / armement — **non représentatif** de l’occupation générale.
- **Période** : Hallstatt–La Tène ; entrées « Bz moyen » dans `Datation globale Tum` — **avant** la fenêtre HALLSTATT stricte du JSON : gérer à part ou étendre le référentiel.
- **Complétude mobilier** : nombreuses colonnes très creuses.

---

*Document basé sur `metadata.json` et les référentiels `data/reference/`.*
