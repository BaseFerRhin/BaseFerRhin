# Prompt d’ingestion — `cag_68_biblio.doc` (CAG Haut-Rhin — bibliographie)

Tu es un agent de données chargé d’**extraire et structurer la bibliographie** du fichier **CAG 68** au service du projet **BaseFerRhin**. Tu ne dois pas supposer le contenu lisible sans **étape de conversion** préalable.

---

## Contexte

- **Projet** : BaseFerRhin — inventaire archéologique de l’âge du Fer, Rhin supérieur.
- **Fichier source** : `data/input/cag_68_biblio.doc` (**Word .doc legacy**, ~225 Ko).
- **Contrainte** : **python-docx ne lit pas le .doc** — conversion obligatoire (**antiword** ou **LibreOffice CLI**).
- **Objectif** : produire une **table de références** exploitable pour enrichir les fiches sites issues du **texte CAG 68** (`cag_68_texte.doc`).
- **Référence** : `data/analysis/cag_68_biblio/metadata.json`

---

## Références obligatoires

| Fichier | Rôle |
|--------|------|
| `data/reference/toponymes_fr_de.json` | Harmonisation des noms géographiques dans titres ou lieux d’édition si besoin. |
| `data/reference/types_sites.json` | Contexte projet (peu utilisé directement ici). |
| `data/reference/periodes.json` | Idem — rattachement indirect via notices plus tard. |
| `data/analysis/cag_68_texte/` | Une fois disponible, texte converti pour **lier** citations ↔ notices (après T4 du texte). |

---

## Tâches

### T1 — Conversion .doc → texte exploitable

1. Créer un répertoire de travail (ex. `data/work/cag_68/`) et y convertir le fichier avec **LibreOffice** (`soffice --headless --convert-to docx` ou `txt`) **ou** **antiword**.
2. Vérifier l’**encodage UTF-8** du résultat ; corriger les remplacements typiques (ligatures, apostrophes).
3. Archiver dans `quality_report.json` la **commande exacte**, la **date** et la **taille** du fichier sortant.

### T2 — Inspection structurelle

1. Lire les **200–400** premières lignes du texte converti et décrire le **pattern** des entrées (séparateurs, numérotation, styles).
2. Proposer une **grammaire de segmentation** (ex. split sur double newline, détection `(19xx|20xx)` pour ancrage).

### T3 — Extraction structurée

1. Parser le corpus en entrées ; champs cibles : `raw_text`, `auteur`, `annee`, `titre`, `revue_ou_lieu`, `pages`, `id_entree` (si numéroté).
2. Conserver **toujours** `raw_text` pour relecture humaine.
3. Marquer `parse_confidence` (HIGH/MEDIUM/LOW) par entrée.

### T4 — Alignement avec le volume principal

1. Lorsque `data/work/cag_68/cag_68_texte.txt` (ou docx) existe, extraire les **motifs de citation** (ex. `[12]`, `Auteur, 1998`) et construire une table de **liens** `citation_id → clé_biblio`.
2. Si le texte n’est pas encore converti, documenter les **prérequis** et produire uniquement la biblio autonome.

### T5 — Contrôle qualité

1. Échantillon **10 %** des entrées : comparaison visuelle texte source ↔ champs parsés.
2. Compter les entrées **incomplètes** (sans année ou sans titre).
3. Lister les **lignes orphelines** (en-têtes de section, notes éditoriales).

### T6 — Export

1. **`data/analysis/cag_68_biblio/bibliographie_structured.csv`** : une ligne par référence + colonnes ci-dessus.
2. **`data/analysis/cag_68_biblio/quality_report.json`** : commande de conversion, stats, taux de confiance, liens vers texte si faits.

---

## Validation

- Fichier converti **non vide** et lisible (spot-check français).
- Au moins **une** méthode de conversion **reproductible** documentée.
- CSV avec colonne **`raw_text`** toujours remplie.

Résumer en **français** : nombre d’entrées extraites, taux d’échec parsing, prochaines étapes pour lien avec `cag_68_texte`.
