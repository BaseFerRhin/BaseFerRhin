# Analyse — `cag_68_biblio.doc`

Document d’analyse pour le fichier **Word binaire legacy** (.doc) contenant la **bibliographie** de la *Carte Archéologique de la Gaule* — **Haut-Rhin (68)**. Les métadonnées proviennent de `metadata.json` du même répertoire.

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `cag_68_biblio.doc` (`data/input/`) |
| **Format** | **Microsoft Word 97-2003** (.doc), **~225 Ko** |
| **Source éditoriale** | **CAG 68** — volume départemental pour le **Haut-Rhin** |
| **Contenu attendu** | Liste bibliographique (ouvrages, articles, rapports) cités dans le volume ; structure habituelle : **entrées alphabétiques ou par auteur**, parfois numérotation liée aux notices |
| **Parsabilité** | **Non** avec `python-docx` (réservé au .docx) ; extraction via **antiword**, **LibreOffice en ligne de commande** (`--headless --convert-to txt/docx`), ou **textutil** (macOS) selon environnement |
| **Confiance globale** | **FAIBLE** (`LOW`) pour l’automatisation immédiate — liée au **format fichier**, pas à la qualité scientifique du contenu |
| **Rôle projet** | **Référence documentaire** pour rattacher les sites BaseFerRhin aux **publications CAG** ; utile pour compléter le champ bibliographique des entités déjà géoréférencées par ailleurs (**pas** une source primaire de coordonnées) |

---

## 2. Schéma

Le .doc **n’expose pas de schéma tabulaire**. Après conversion en texte ou docx, la structure logique typique comprend :

- **Blocs d’entrées** séparés par sauts de ligne doubles ou retraits.
- **Auteur(s), année, titre**, revue ou maison d’édition.
- Éventuelles **clés de renvoi** vers les notices communales ou les numéros de sites (à identifier par motifs après extraction).

Documenter le **pattern réel** (regex, préfixes numériques) une fois le texte brut produit.

---

## 3. Modèle de données

- **Unité documentaire** : **référence bibliographique** (une entrée = un dict avec champs `auteur`, `annee`, `titre`, `lieu_edition`, `revue`, `pages`, `id_entree` si numéroté).
- **Lien vers les sites** : en général **indirect** (citations dans le texte des notices) — la biblio seule ne suffit pas à créer des géométries ; elle sert au **maillage citation ↔ notice ↔ site** après alignement sur `cag_68_texte` ou index.

---

## 4. Qualité

- **Contenu** : attendu comme **curated** par les auteurs de la CAG — forte **autorité scientifique** une fois extrait.
- **Technique** : risques de **perte de mise en forme** (italiques, exposants), **césures de mots** en fin de ligne, **caractères spéciaux** lors de la conversion ; relecture spot sur un échantillon nécessaire.
- **Couverture** : bibliographie **68** complémentaire de la **67** (Bas-Rhin) dans BaseFerRhin — attention aux **doublons inter-départements** (ouvrages régionaux communs).

---

## 5. Mapping BaseFerRhin

| Référentiel | Fichier | Usage |
|-------------|---------|--------|
| Types / périodes | [`data/reference/types_sites.json`](../../reference/types_sites.json), [`data/reference/periodes.json`](../../reference/periodes.json) | Peu directement concernés par la biblio seule ; utiles lors du **rattachement** aux fiches site |
| Toponymes | [`data/reference/toponymes_fr_de.json`](../../reference/toponymes_fr_de.json) | Si titres ou lieux d’édition contiennent des variantes toponymiques |

---

## 6. Stratégie d’ingestion

1. **Conversion** :  
   - Priorité **LibreOffice** : `soffice --headless --convert-to docx` ou `txt` vers un répertoire `data/work/cag_68/` ;  
   - Alternative **antiword** pour .txt rapide ;  
   - Vérifier la **lisibilité** (encodage UTF-8).
2. **Si docx** : optionnellement parser avec `python-docx` par paragraphes ; **si txt** : segmentation par lignes vides / motifs d’année.
3. **Structuration** : règles heuristiques (ligne commençant par majuscule + virgule = auteur ; présence `(19xx)` ou `20xx` = année) — **ajuster** après revue humaine sur 20–30 entrées.
4. **Alignement** : lier les entrées aux **clés de citation** utilisées dans `cag_68_texte` (une fois ce fichier converti) — ex. `[Auteur, année]` ou numéros entre crochets.
5. **Export** : table `cag68_bibliographie.csv` (une ligne par référence) + fichier de **traçabilité** (hash du fichier source converti).
6. **Priorité** : ce fichier est **secondaire** par rapport à **`cag_68_texte.doc`** pour la création d’entités site ; traiter la biblio **après** ou **en parallèle** du texte principal.

---

## 7. Limites

- **Pas d’accès direct au contenu** dans l’état .doc sans conversion.
- **Parsing bibliographique automatique** reste **approximatif** (noms composés, titres multi-lignes).
- **Pas de coordonnées** : ne remplace pas l’extraction des notices communales.
- **Dépendance éditoriale** : toute republication doit respecter les **droits** sur la CAG.

---

*Document aligné sur `data/analysis/cag_68_biblio/metadata.json`.*
