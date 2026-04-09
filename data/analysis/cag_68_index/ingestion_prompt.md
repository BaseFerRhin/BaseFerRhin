# Prompt d’ingestion — `cag_68_index.doc` (CAG Haut-Rhin — index)

Tu es un agent de données chargé d’**extraire l’index** du volume **CAG 68** et de le **relier** au texte des notices lorsque celui-ci est disponible. La première étape est toujours la **conversion** du .doc legacy.

---

## Contexte

- **Projet** : BaseFerRhin.
- **Fichier** : `data/input/cag_68_index.doc` (~236 Ko, **.doc** non lisible par `python-docx`).
- **Objectif** : produire une **table d’entrées d’index** avec renvois (pages ou sections) pour navigation et enrichissement sémantique.
- **Dépendance** : le **fichier prioritaire** du triptyque CAG 68 est **`cag_68_texte.doc`** — l’index est complémentaire.
- **Référence** : `data/analysis/cag_68_index/metadata.json`

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/toponymes_fr_de.json` | Normalisation des lemmes toponymiques. |
| `data/reference/types_sites.json` | Aide à classifier les entrées thématiques (mots-clés types de sites). |
| `data/reference/periodes.json` | Détection de périodes dans les lemmes d’index. |
| Texte converti `cag_68_texte` | Cible des **renvois** (chemins sous `data/work/cag_68/` une fois générés). |

---

## Tâches

### T1 — Conversion

1. Convertir `cag_68_index.doc` en **UTF-8** `.txt` ou `.docx` via **LibreOffice** ou **antiword** (même procédure que `cag_68_biblio`).
2. Vérifier la **préservation des tabulations** ; si perdues, documenter l’impact dans `quality_report.json`.

### T2 — Analyse de forme

1. Échantillonner **100+ lignes** et classifier les **motifs** : entrée seule, entrée + suite de pages, entrées hiérarchisées (indentation).
2. Choisir une stratégie : **regex par ligne** ou **état machine** (lecture ligne à ligne avec pile d’indentation).

### T3 — Extraction des entrées

1. Pour chaque entrée, produire : `entree`, `renvois_bruts`, `pages` (liste normalisée d’entiers si possible), `raw_line`, `parse_confidence`.
2. Gérer les **renvois multiples** séparés par virgules ou points-virgules selon le fichier réel.

### T4 — Résolution des renvois

1. Si `cag_68_texte` converti existe : mapper `pages` aux **offsets** ou **titres de notices** (détection de titres « Commune de … », « Ville de … », etc., comme pour le **CAG 67**).
2. Si le texte n’est pas prêt : laisser `target_anchor=null` et lister les **prérequis** dans le rapport.

### T5 — Enrichissement toponymique

1. Matcher les entrées contre `toponymes_fr_de.json` (`canonical` et `variants`) ; tagger `toponyme_match` (bool + clé).

### T6 — Export

1. **`data/analysis/cag_68_index/index_entries.csv`**
2. **`data/analysis/cag_68_index/quality_report.json`** : commande de conversion, stats d’entrées, taux de renvois résolus, problèmes de tabulation.

---

## Validation

- Fichier source converti **lisible**.
- CSV avec au moins **80 %** des lignes ayant un `renvois_bruts` non vide **ou** justification des lignes exclues (en-têtes).
- Documentation explicite des **limites** si les numéros de page du .doc ne correspondent pas au PDF papier (décalages d’édition).

Résumer en **français** : nombre d’entrées, renvois résolus vers le texte, blocages.
