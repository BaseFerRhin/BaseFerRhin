# Analyse — `cag_68_index.doc`

Document d’analyse pour le fichier **Word binaire legacy** (.doc) contenant l’**index** de la *Carte Archéologique de la Gaule* — **Haut-Rhin (68)**. Les métadonnées proviennent de `metadata.json` du même répertoire.

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `cag_68_index.doc` (`data/input/`) |
| **Format** | **Microsoft Word 97-2003** (.doc), **~236 Ko** |
| **Source éditoriale** | **CAG 68** — volume départemental **Haut-Rhin** |
| **Contenu attendu** | **Index alphabétique** (toponymes, noms propres, thèmes) avec **renvois** vers pages ou sections du volume (notices communales, cartes) |
| **Parsabilité** | Identique aux autres .doc : **conversion** requise (**LibreOffice CLI**, **antiword**) avant tout traitement Python moderne |
| **Confiance globale** | **FAIBLE** (`LOW`) pour l’ingestion automatisée brute ; **ÉLEVÉE** pour la **valeur d’indexation** une fois le texte extrait et nettoyé |
| **Rôle projet** | Accélérer la **recherche par mot-clé** (commune, site, personnage, type d’objet) et fournir des **ponts** vers les pages du fichier texte converti ; complément au **plein texte** de `cag_68_texte.doc` |

---

## 2. Schéma

Pas de schéma relationnel natif. Après extraction, modèle logique recommandé :

| Champ logique | Description |
|-----------------|-------------|
| `entree` | Lemme ou groupe nominal indexé |
| `sous_entrees` | éventuelles subdivisions (indentation) |
| `renvois` | liste de cibles (numéros de page, clés « commune X ») |
| `raw_line` | ligne source pour audit |

La structure exacte (**tabulations**, **points de suite**, **numéros de page**) doit être inférée sur le fichier converti.

---

## 3. Modèle de données

- **Granularité** : **une ligne ou bloc d’index** = une entrée d’index avec **un ou plusieurs renvois**.
- **Relations** : les renvois relient vers des **ancres** dans le texte des notices — à résoudre après segmentation de `cag_68_texte` (structure analogue au **CAG 67/1** en PDF dans le sous-projet Bas-Rhin).
- **Pas de coordonnées** : l’index oriente vers le **discours** ; le géoréférencement reste dans les **notices** ou cartes.

---

## 4. Qualité

- **Risques de conversion** : césures, perte des **tabulations** (critiques pour distinguer entrée / renvoi), caractères spéciaux.
- **Homonymie** : entrées identiques pour **lieux différents** — désambiguïsation par **contexte** ou **page**.
- **Complétude** : l’index couvre ce que les auteurs ont jugé indexable — **pas exhaustif** de tous les micro-toponymes des notices.

---

## 5. Mapping BaseFerRhin

| Référentiel | Fichier | Usage |
|-------------|---------|--------|
| Toponymes | [`data/reference/toponymes_fr_de.json`](../../reference/toponymes_fr_de.json) | Normaliser les entrées d’index correspondant à des **communes** ou **lieux** connus du référentiel |
| Types / périodes | [`data/reference/types_sites.json`](../../reference/types_sites.json), [`data/reference/periodes.json`](../../reference/periodes.json) | Faciliter le **tagging** des entrées thématiques (« nécropole », « La Tène », …) si présentes comme lemmes |

---

## 6. Stratégie d’ingestion

1. **Convertir** `.doc` → `.txt` ou `.docx` (LibreOffice ou antiword), comme pour `cag_68_biblio.doc` et `cag_68_texte.doc`.
2. **Nettoyer** fins de ligne et espaces ; préserver les **tabulations** si présentes (ne pas les réduire aveuglément).
3. **Segmenter** les entrées : heuristiques sur **majuscules**, **virgules**, **points de suite**, **plages de pages** (regex `\d+(-\d+)?`).
4. **Lier** chaque renvoi à une **ancre** dans le texte converti du volume principal (numéro de page estimé + recherche de sous-chaîne, ou alignement sur titres de notices **Commune**).
5. **Exporter** `cag68_index_entries.csv` avec colonnes `entree`, `renvois_bruts`, `pages`, `raw_line`, `confidence`.
6. **Ordre de priorité** : traiter **après** ou **en parallèle** de `cag_68_texte` — l’index seul a une utilité limitée sans **corpus des notices** segmenté.

---

## 7. Limites

- **Dépendance forte** au **texte principal** pour interpréter les renvois.
- **Conversion** peut dégrader la **mise en page** tabulaire de l’index.
- **Pas de substitut** à l’extraction structurée des **fiches par commune** dans `cag_68_texte.doc`.
- **Droits d’auteur** : respecter les conditions d’usage de l’ouvrage CAG et la politique de publication du projet.

---

*Document aligné sur `data/analysis/cag_68_index/metadata.json`.*
