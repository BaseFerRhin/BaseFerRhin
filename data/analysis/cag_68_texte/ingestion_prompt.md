# Prompt d’ingestion — `cag_68_texte.doc` (CAG Haut-Rhin — texte des notices)

Tu es un agent de données chargé d’**extraire des fiches sites** depuis le **texte principal** de la **CAG 68**. Ce fichier est la **priorité absolue** du corpus CAG 68 pour BaseFerRhin. Tu dois **convertir** le .doc legacy avant parsing, puis appliquer une logique **proche du traitement CAG Bas-Rhin (67/1 PDF)** décrit dans le sous-projet associé.

---

## Contexte

- **Projet** : BaseFerRhin — inventaire de l’âge du Fer, Rhin supérieur (FR/DE).
- **Fichier** : `data/input/cag_68_texte.doc` (~1449 Ko).
- **Contrainte** : pas de lecture directe fiable avec `python-docx` sur le .doc — **LibreOffice headless** ou **antiword** en préalable.
- **Objectif** : segmenter les **notices communales**, puis les **sous-unités sites**, extraire **description**, **chronologie**, **type de vestige**, **références**, et préparer l’**alignement** avec `types_sites.json`, `periodes.json`, `toponymes_fr_de.json`.
- **Référence** : `data/analysis/cag_68_texte/metadata.json`

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/types_sites.json` | Codes et alias pour classification des sites / vestiges. |
| `data/reference/periodes.json` | Normalisation Hallstatt / La Tène / transition. |
| `data/reference/toponymes_fr_de.json` | Concordance des communes et variantes. |
| `data/sources/golden_sites.csv` | Validation et contrôle qualité si disponible. |
| Sous-projet / scripts **CAG 67** | Réutiliser ou **dupliquer adapté** les patterns de segmentation des notices (PDF 67) — même esprit : titres de communes, blocs, regex chrono. |

---

## Tâches

### T1 — Conversion et normalisation

1. Convertir `cag_68_texte.doc` vers **`docx` UTF-8** (préféré) ou **`txt`** dans `data/work/cag_68/`.
2. Documenter la commande exacte dans `quality_report.json`.
3. Si **docx** : optionnellement utiliser `python-docx` pour parcourir **styles** (`Heading 1`, etc.) ; si **txt** : s’appuyer sur **motifs de titres** (lignes en majuscules, préfixes « Commune », etc.).

### T2 — Segmentation des notices

1. Identifier les **frontières de notices** (une commune = une section principale).
2. Extraire `commune_nom` pour chaque section ; normaliser avec `toponymes_fr_de.json` et préparer le **code INSEE 68** (table externe ou base admin si disponible dans le dépôt).
3. Découper chaque notice en **blocs candidats site** (numérotation, paragraphes, listes).

### T3 — Extraction champs par bloc

Pour chaque bloc, produire au minimum :  
`raw_text`, `nom_site_candidate`, `description`, `periode_brute`, `type_brut`, `biblio_snippets`, `parse_confidence`.

Utiliser des **regex** et listes de **patterns** issus de `periodes.json` (`patterns_fr`) et `types_sites.json` (`aliases.fr`).

### T4 — Classification BaseFerRhin

1. Mapper `type_brut` → code `type_site` (priorité au plus spécifique).
2. Mapper `periode_brute` → `periode` / `sous_periode` / bornes numériques si mentionnées.
3. Filtrer ou **tagger** `age_du_fer_relevant` (bool) selon règles projet pour ne pas mélanger indistinctement toutes périodes.

### T5 — Rattachement spatial et inter-sources

1. Sans coordonnées natives : proposer **clé d’appariement** (`commune` + tokens lieu-dit) vers `data/output/sites.csv`, **EA**, ou autres couches.
2. Si coordonnées présentes dans le texte (rare), les parser et valider bbox.

### T6 — Export

1. **`data/analysis/cag_68_texte/notices_sites.csv`** (ou JSONL) avec schéma compatible l’export global du projet :  
   `site_id`, `nom_site`, `commune`, `departement` (68), `pays`, `type_site`, `longitude`, `latitude`, `x_l93`, `y_l93`, `periode`, `sous_periode`, `datation_debut`, `datation_fin`, `confiance`, `source`, `description`, `bibliographie`  
   — `site_id` : préfixe `CAG68_` + slug stable (commune + hash court du `raw_text`).
2. **`data/analysis/cag_68_texte/quality_report.json`** : stats de conversion, taux de blocs classés HIGH/MEDIUM, liste des communes sans découpage clair, liens vers fichiers convertis.

---

## Validation

- Fichier converti **> 100 Ko** texte utile (sanity check) et **UTF-8** valide.
- Au moins **3** communes **manuellement** spot-checkées : rendu du parseur vs texte source.
- Référence explicite dans le rapport à la **stratégie CAG 67** (même structure de notices) et écarts observés.

À la fin, résumer en **français** : nombre de blocs extraits, couverture communale estimée, taux âge du Fer, blocages majeurs.
