# Prompt d’ingestion — `ea_fr.dbf` (Entités Archéologiques France)

Tu es un agent de données chargé d’ingérer l’extrait **EA-FR** (DBF) dans le projet **BaseFerRhin**. Tu dois gérer les **doublons** sur `EA_NATCODE` et **parser** le champ composite **`EA_IDENT`**.

---

## Contexte

- **Projet** : BaseFerRhin — inventaire de l’âge du Fer du Rhin supérieur (et sources apparentées).
- **Fichier** : `data/input/ea_fr.dbf`
- **Format** : DBF, **29 colonnes**, **42 lignes**, encodage **latin-1**.
- **Identifiant national** : `EA_NATCODE` (**33** uniques — plusieurs lignes pour certains codes).
- **Champ critique** : `EA_IDENT` — texte structuré avec séparateurs **` / `**, pouvant inclure des segments vides.
- **Géolocalisation** : `X_DEGRE`, `Y_DEGRE` (décimales) ; `X_SAISI`, `Y_SAISI` (chaînes) ; `GEOMETRIE` ∈ {POL, CER, PNT}.
- **Chronologie** : `CHRONO_DEB`, `CHRONO_FIN` (codes EUR*), `NUMERIQUE_` souvent vide, mentions textuelles dans `EA_IDENT`.
- **Référence** : `data/analysis/ea_fr/metadata.json`

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Classification des types de sites (HABITAT, NECROPOLE, …). |
| `data/reference/periodes.json` | Hallstatt, La Tène, transition ; patterns FR pour libellés type « Age du fer ». |
| `data/reference/toponymes_fr_de.json` | Normalisation des noms de communes. |
| `data/sources/golden_sites.csv` | Contrôle et déduplication inter-sources. |
| `data/analysis/ea_fr/metadata.json` | Schéma et statistiques. |

---

## Tâches

### T1 — Chargement et parsing `EA_IDENT`

1. Charger le DBF (latin-1), dtypes adaptés (conserver `X_SAISI`/`Y_SAISI` en texte jusqu’à validation).
2. Implémenter `parse_ea_ident(s)` qui retourne un dict avec au minimum :  
   `ident_num`, `numero_entite`, `commune_nom`, `segment_vide_1`, `lieu`, `periode_texte`, `vestige_texte`  
   — **ajuster** les clés après inspection des **42** lignes réelles (certaines positions peuvent varier).
3. Comparer le résultat du parser aux colonnes **`NUMERO`**, **`LIEU_IGN`**, **`VESTIGES`** : en cas d’écart, privilégier les **colonnes structurées** pour l’export et utiliser `EA_IDENT` en **contrôle**.

### T2 — Déduplication par `EA_NATCODE`

1. Grouper par `EA_NATCODE` ; pour chaque groupe, produire **une** ligne canonique.
2. Règle par défaut : conserver la ligne avec **`SURFACE`** la plus informative et **`VESTIGES`** non vide ; si égalité, concaténer les descriptions uniques dans un champ `notes_fusion` ; **documenter** toute règle alternative dans `quality_report.json`.
3. Signaler dans le rapport les codes ayant **>1** ligne source.

### T3 — Classification type et période

1. **`VESTIGES`** (+ segment vestige de `EA_IDENT`) → code `type_site` via `types_sites.json` (`aliases.fr`).
2. **Chronologie** : construire une table `eur_code → periode_projet` (ex. EURFER → fer pré-romain large + affinage par texte) ; croiser avec `NUMERIQUE_` pour `datation_debut`/`datation_fin` si renseigné.
3. Libellés « Age du bronze - Age du fer » → gérer **incertitude** (période multiple ou confiance **MEDIUM**/**LOW** selon règle projet).

### T4 — Géoréférencement et géométrie

1. Valider que `X_DEGRE`, `Y_DEGRE` tombent dans une bbox plausible **Grand Est / 67** (ex. lon ~7–8, lat ~48–49) ; exceptions listées dans le rapport.
2. Projeter en **EPSG:2154** (`x_l93`, `y_l93`).
3. Porter dans l’export un champ `geometrie_ea` = valeur de `GEOMETRIE` ; si le dépôt fournit un shapefile EA correspondant plus tard, prévoir clé de jointure `EA_NATCODE`.

### T5 — Rattachement inter-sources

1. Matcher d’abord sur **`EA_NATCODE`** avec tout site déjà porteur de ce code dans `data/output/sites.csv`.
2. Sinon, matching spatial (buffer, ex. 50–150 m) + **commune** normalisée (`toponymes_fr_de.json`).
3. Consigner paires suspectes dans `quality_report.json`.

### T6 — Export

1. **`data/analysis/ea_fr/sites_cleaned.csv`** avec colonnes minimales :  
   `site_id`, `ea_natcode`, `nom_site`, `commune`, `departement`, `pays`, `type_site`, `longitude`, `latitude`, `x_l93`, `y_l93`, `periode`, `sous_periode`, `datation_debut`, `datation_fin`, `confiance`, `geometrie_ea`, `surface`, `source`, `description`  
   — `site_id` recommandé : préfixe `EAFR_` + `EA_NATCODE` (ou identifiant stable post-fusion).
2. **`data/analysis/ea_fr/quality_report.json`** : stats parser, doublons fusionnés, anomalies géographiques, mapping EUR*.

---

## Validation

- **42** lignes lues ; **33** sites uniques après fusion (ou justifier un autre nombre si règle métier différente).
- 100 % des lignes exportées avec **lon/lat** valides sauf exceptions documentées.
- Liste des **`EA_NATCODE`** multi-lignes dans le rapport.

Résumer en **français** : sites exportés, taux de fusion, anomalies principales.
