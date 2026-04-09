# Analyse — `ea_fr.dbf`

Document d’analyse pour l’extrait **Entités Archéologiques France** (table DBF, 42 lignes × 29 colonnes) centré sur des sites des **Bas-Rhin (67)** (âge du Bronze / âge du Fer notamment). Les métriques proviennent de `metadata.json` du même répertoire.

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `ea_fr.dbf` (`data/input/`) |
| **Format** | DBF, encodage **latin-1** |
| **Source** | **Entités Archéologiques (EA)** — base nationale de l’inventaire archéologique (France) |
| **Volume** | **42** lignes, **29** colonnes |
| **Identifiants** | **`EA_NATCODE`** : **33** valeurs distinctes → **doublons** ou révisions multiples (max **3** lignes par code selon `data_model`) |
| **Géographie** | Codes **`NUMERO`** / **`COMMUNE_PP`** type **« 67 xxx »** (Bas-Rhin) ; coordonnées **`X_DEGRE`**, **`Y_DEGRE`** (WGS84 attendu) et **`X_SAISI`**, **`Y_SAISI`** (saisie métrique, ex. ~1 035 000 / 6 844 000 — cohérent avec Lambert ou système local) |
| **Contenu** | Champs structurés (vestiges, géométrie, surface) + champ **`EA_IDENT`** : **texte composite** à **découper** (numéro / commune / adresse ou lieu / période / type de vestige) |
| **Confiance globale** | **ÉLEVÉE** (`HIGH`) côté métadonnées automatiques ; **MOYENNE** en pratique métier à cause du **parsing** de `EA_IDENT` et des **doublons** par `EA_NATCODE` |
| **Rôle projet** | Rattachement **officiel** à l’identifiant national EA ; complément **ponctuel** (42 lignes) à l’inventaire BaseFerRhin pour le **67** ; base de **liens** vers dossiers et géométries (POL/CER/PNT) |

---

## 2. Schéma

*Colonnes clés ; voir `metadata.json` pour la liste complète et les taux de remplissage.*

| Colonne | Type | Remplissage | Notes |
|---------|------|-------------|--------|
| `EA_NATCODE` | texte | 100 % | Code national EA |
| `EA_IDENT` | texte | 100 % | **Chaîne multi-segments** (séparateur « / » dans les échantillons) : id, numéro d’entité, commune, lieu, période, vestige |
| `NUMERO` | texte | 100 % | Ex. `67 150 0014` |
| `COMMUNE_PP` | texte | 100 % | Code commune partiel (ex. `67 150`) |
| `NUMORDRE` | entier | 100 % | Ordre au sein de la commune |
| `NOMUSUEL` | texte | 100 % | Nom d’usage (souvent vide) |
| `LIEU_IGN` | texte | 100 % | Libellé de localisation (rue, lieu-dit) |
| `LIEU_CADAS` | texte | 100 % | Référence cadastrale (souvent vide) |
| `VESTIGES` | texte | 100 % | Type de vestige (silo, fosse, inhumation, …) |
| `NATURE_VES` | texte | 100 % | Codes courts (ex. **S** / **I**) |
| `CHRONO_DEB` / `CHRONO_FIN` | texte | 100 % | Thésaurus type **EURFER------**, **EURBRO------** (Europe Fer / Bronze) |
| `CHRONO_FOU` | texte | 100 % | Fouille oui/non |
| `NUMERIQUE_` | flottant | **~14 %** | Bornes chronologiques numériques quand renseignées (ex. -750, -52) |
| `X_SAISI`, `Y_SAISI` | texte | 100 % | Coordonnées saisies (chaînes numériques) |
| `X_DEGRE`, `Y_DEGRE` | flottant | 100 % | Longitude / latitude |
| `SURFACE` | flottant | 100 % | Surface emprise |
| `GEOMETRIE` | texte | 100 % | **POL** / **CER** / **PNT** |
| `EMPRISE` | texte | 100 % | Ex. **LIN** ou vide |
| `ANNEE_DECO` | flottant | ~90,5 % | Année découverte |
| Autres (`NUMERO_DRA`, `CHRONO_DOU`, `CHRONO_PER`, `COMMENT_CH`, `PARCELLES`, …) | divers | variable | Peu discriminants dans cet extrait (souvent vides ou constantes) |

---

## 3. Modèle de données

- **Granularité nominale** : **une entité archéologique** = un **`EA_NATCODE`** ; la table contient toutefois **plusieurs lignes pour certains codes** (jusqu’à 3) — à traiter par **agrégation** ou **choix de version** (dernière saisie, non-contradiction géométrique, etc.).
- **`EA_IDENT`** : redondant avec plusieurs champs déjà séparés mais sert de **filet de relecture** et peut contenir des **segments non alignés** sur `VESTIGES` / chrono si la saisie a évolué.
- **Chronologie** : double système — **codes EUR*** (thésaurus) et **`NUMERIQUE_`** (optionnel) ; alignement à faire avec **Hallstatt / La Tène** via règles et `periodes.json`.
- **Géométrie** : le champ `GEOMETRIE` qualifie le type ; l’emprise réelle peut nécessiter un **fichier géométrique joint** (si livraison complète EA) — ici seules les **coordonnées ponctuelles ou centroïdes** sont visibles dans les attributs.

---

## 4. Qualité

**Points positifs**

- Coordonnées décimales **100 %** renseignées (`X_DEGRE`, `Y_DEGRE`).
- Champs d’identification et de vestige **généralement complets**.
- Référence nationale **`EA_NATCODE`** stable pour interopérabilité.

**Problèmes**

1. **`EA_IDENT`** : nécessite un **parser robuste** (séparateurs, champs vides consécutifs ` /  / ` dans les échantillons).
2. **Doublons** `EA_NATCODE` : **42** lignes pour **33** codes — risque de **double comptage** sans agrégation.
3. **`NUMERIQUE_`** : **~86 %** de valeurs nulles dans cet extrait.
4. **`NOMUSUEL`**, **`LIEU_CADAS`**, **`EMPRISE`** : peu informatifs ou vides — peu de valeur ajoutée sans autre source.

**Synthèse** : données **structurées et localisées** ; qualité **ingestion** dépend du **traitement des doublons** et du **parsing** de `EA_IDENT`.

---

## 5. Mapping BaseFerRhin

| Référentiel | Fichier | Usage |
|-------------|---------|--------|
| Types de sites | [`data/reference/types_sites.json`](../../reference/types_sites.json) | Mapper `VESTIGES` (silo, fosse, inhumation, …) vers **HABITAT**, **NECROPOLE**, **DEPOT**, etc. ; croiser avec le dernier segment de `EA_IDENT` |
| Périodes | [`data/reference/periodes.json`](../../reference/periodes.json) | Traduire **EURFER------** / **EURBRO------** et textes « Age du fer », « Age du bronze » en périodes canoniques ; utiliser `NUMERIQUE_` quand présent pour affiner |
| Toponymes | [`data/reference/toponymes_fr_de.json`](../../reference/toponymes_fr_de.json) | Harmoniser noms de communes extraits de `EA_IDENT` avec le référentiel communal du projet |

---

## 6. Stratégie d’ingestion

1. **Lire le DBF** (latin-1) et profiler les **9** lignes « en trop » vs `EA_NATCODE` uniques.
2. **Parser `EA_IDENT`** : découper sur `/` (trim) ; mapper positionnellement ou par motifs (regex numéro `67 \d{3} \d{4}`, noms propres, segments « Age du … »).
3. **Agréger par `EA_NATCODE`** : règle explicite (fusion descriptifs, conservation des géométries les plus précises, ou ligne la plus récente si métadonnée de date disponible ailleurs).
4. **Normaliser chronologie** : table de correspondance **EUR\*** → intervalles ou étiquettes ; complément par `NUMERIQUE_` et texte libre dans `EA_IDENT`.
5. **Mapper `VESTIGES` + nature** vers `types_sites.json` ; flag **confiance** selon cohérence EA_IDENT / VESTIGES / chrono.
6. **Projeter** WGS84 → Lambert-93 pour cohérence avec les autres couches ; joindre aux inventaires existants par **EA_NATCODE** puis par **distance** + commune.

---

## 7. Limites

- **Extrait localisé** (42 lignes, 67) : ne représente **pas** l’ensemble des EA d’Alsace.
- **Thésaurus EUR\*** : mapping vers Hallstatt/La Tène reste une **interprétation** — documenter les tables de correspondance.
- **Géométrie** : champs **POL/LIN** sans fichier vectoriel joint dans ce seul DBF limitent la restitution des **emprises réelles**.
- **Données réglementaires** : respecter les **conditions d’usage** du service Patrimoine / EA pour redistribution ou affichage public.

---

*Document aligné sur `data/analysis/ea_fr/metadata.json`.*
