# Analyse — `cag_68_texte.doc`

Document d’analyse pour le fichier **Word binaire legacy** (.doc) du **texte principal** de la *Carte Archéologique de la Gaule* — **Haut-Rhin (68)** : notices communales et descriptions de sites. Les métriques de fichier proviennent de `metadata.json` du même répertoire.

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `cag_68_texte.doc` (`data/input/`) |
| **Format** | **Microsoft Word 97-2003** (.doc), **~1449 Ko** — **volume le plus riche** des trois livrables CAG 68 (.biblio, .index, .texte) |
| **Source** | **CAG 68** — inventaire archéologique départemental **Haut-Rhin** |
| **Contenu attendu** | **Notices par commune** (ordre alphabétique ou géographique), mention des **sites**, **vestiges**, **chronologies**, **bibliographie inline** ou renvois ; structure **comparable** au volume **CAG Bas-Rhin (67)** traité ailleurs sous forme **PDF** dans le sous-projet dédié |
| **Parsabilité** | Extraction via **LibreOffice CLI** ou **antiword** ; ensuite **pipeline texte** (regex, segmentation par titres de notices) analogue au **CAG 67/1** |
| **Confiance globale** | **FAIBLE** (`LOW`) tant que le .doc n’est pas converti ; **ÉLEVÉE** pour la **valeur scientifique** une fois structuré |
| **Rôle projet** | **Source prioritaire** pour le **68** dans BaseFerRhin : création / enrichissement d’**entités sites**, **descriptions**, **datations textuelles**, liens biblio — au même niveau d’ambition que l’exploitation du PDF CAG 67 |

---

## 2. Schéma

Le document est **semi-structuré**. Après conversion, schéma cible pour l’ingestion :

| Niveau | Exemple de signaux | Champs dérivés |
|--------|-------------------|----------------|
| **Notice** | Titre « Commune de X », « Ville de Y », saut de page | `commune`, `offset_debut`, `offset_fin` |
| **Site / paragraphe** | Numérotation, tirets, noms propres en tête de phrase | `nom_site_candidate`, `description`, `bibliographie_inline` |
| **Éléments factuels** | « Âge du Fer », « La Tène », « tumulus », coordonnées parfois absentes | `periode_texte`, `type_vestige`, `notes` |

Les **motifs exacts** dépendent du fichier converti et doivent être **calibrés** sur un échantillon de notices (3–5 communes).

---

## 3. Modèle de données

- **Granularité recommandée** : **site** (ou **sous-notice**) comme enregistrement cible, rattaché à **`commune`** (INSEE 68 à croiser).
- **Relations** : liens vers entrées de **`cag_68_biblio`** via **clés de citation** ; liens inverse depuis **`cag_68_index`**.
- **Géoréférencement** : souvent **textuel** (lieu-dit, cadastre) — nécessité de **géocodage** externe ou croisement avec **EA**, **ArkeoGIS**, orthophotos ; rarement des coordonnées WGS84 explicites dans le texte.

---

## 4. Qualité

- **Richesse** : volume important → **couverture** départementale substantielle pour le **Haut-Rhin**.
- **Risques** : **OCR/ conversion** (si le .doc provient d’une numérisation), **notes de bas de page** perdues ou mal placées, **caractères spéciaux** alsaciens.
- **Cohérence interne** : à valider par **recoupement** avec quelques sites **déjà connus** (golden) pour calibrer le parseur.

---

## 5. Mapping BaseFerRhin

| Référentiel | Fichier | Usage |
|-------------|---------|--------|
| Types de sites | [`data/reference/types_sites.json`](../../reference/types_sites.json) | Mapper vestiges et vocables (enceinte, nécropole, silo, fosse, …) vers codes canoniques |
| Périodes | [`data/reference/periodes.json`](../../reference/periodes.json) | Normaliser Hallstatt, La Tène, transitions ; gérer formulations « second âge du Fer », etc. |
| Toponymes | [`data/reference/toponymes_fr_de.json`](../../reference/toponymes_fr_de.json) | Harmoniser **communes** et **variantes** fr/de pour le 68 et le transfrontalier |

---

## 6. Stratégie d’ingestion

1. **Convertir** `cag_68_texte.doc` → **.docx** ou **.txt** UTF-8 avec **LibreOffice** (`soffice --headless --convert-to …`) ou **antiword** ; éviter les pertes de structure (titres) — **docx** préférable si la hiérarchie de styles est conservée.
2. **Parser** le texte avec une approche **alignée sur le sous-projet CAG 67 (PDF)** : détection des **titres de notices**, segmentation en **blocs site**, extraction des **mentions chronologiques** et **typologiques** (regex + dictionnaires dérivés de `types_sites.json` / `periodes.json`).
3. **Extraire** la **commune** pour chaque bloc (titre de notice ou métadonnée de section).
4. **Construire** des fiches intermédiaires JSON/CSV : `commune`, `nom_site`, `description`, `periode_brute`, `type_brut`, `refs_biblio`, `confiance_parse`.
5. **Enrichir spatialement** : appariement par nom de lieu + commune avec d’autres couches ; géocodage si politique du projet le permet.
6. **Orchestration** : ce fichier est la **priorité n°1** parmi les trois .doc CAG 68 ; `cag_68_biblio` et `cag_68_index` se branchent ensuite.

---

## 7. Limites

- **Format source** : chaîne d’outils plus lourde que pour un PDF « texte natif » ; qualité variable selon conversion.
- **Ambiguïtés** : un paragraphe peut décrire **plusieurs sites** — peut nécessiter **découpage manuel** ou règles NLP plus fines.
- **Pas de garantie** de couverture **âge du Fer seul** : filtrage métier requis en aval.
- **Droits** : respecter la **licence / usage** de la source CAG pour toute diffusion.

---

*Document aligné sur `data/analysis/cag_68_texte/metadata.json`.*
