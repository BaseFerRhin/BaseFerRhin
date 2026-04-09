# Analyse — `2026_afeaf_lineaire.dbf`

Document d’analyse pour la table d’attributs **DBF** (27 lignes × 9 colonnes) associée à des entités linéaires **AFEAF** (Association Française pour l’Étude de l’Âge du Fer), complémentaire aux inventaires ponctuels du projet **BaseFerRhin**. Les métriques proviennent de `metadata.json` du même répertoire.

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `2026_afeaf_lineaire.dbf` (`data/input/`) |
| **Format** | DBF (table attributaire type shapefile), encodage **latin-1** |
| **Source** | **AFEAF** — données relatives à des **traces linéaires** (fossés, structures allongées, indices) documentées dans le cadre de l’étude de l’âge du Fer |
| **Volume** | **27** enregistrements, **9** champs ; **27** identifiants uniques (`id`) |
| **Couverture géographique** | **France** ; départements **Haut-Rhin** et **Bas-Rhin** ; **17** communes distinctes (échantillon : Bisel, Bouxwiller, Oltingue, etc.) |
| **Contenu sémantique** | Champs nommés **a–h** (non documentés dans le fichier) ; interprétation par échantillonnage : pays, département, commune, lieu-dit, catégorie fonctionnelle courte, chronologie, descriptions archéologiques détaillées |
| **Confiance globale** | **ÉLEVÉE** au sens « complétude des cellules » (100 % de remplissage) ; **MOYENNE** au sens « sémantique explicite » (noms de colonnes génériques, dépendance à une géométrie .shp externe non analysée ici) |
| **Rôle projet** | Enrichissement **ponctuel et linéaire** du corpus alsacien ; utile pour croiser **indices de site**, **habitats** et séquences chronologiques textuelles avec les sites inventoriés ; volume **très réduit** → plutôt **échantillon qualitatif** que statistique de masse |

---

## 2. Schéma

| Colonne | Type (métadonnées) | Remplissage | Uniques | Lecture interprétative |
|---------|-------------------|-------------|---------|----------------------|
| `id` | entier | 100 % | 27 | Clé technique locale |
| `a` | texte | 100 % | 1 | **Pays** — valeur observée : « France » |
| `b` | texte | 100 % | 2 | **Département** — « Haut-Rhin », « Bas-Rhin » |
| `c` | texte | 100 % | 17 | **Commune** |
| `d` | texte | 100 % | 24 | **Lieu-dit** / micro-toponyme |
| `e` | texte | 100 % | 2 | **Catégorie courte** — ex. « indice de site », « habitat » |
| `f` | texte | 100 % | 21 | **Chronologie** — texte libre ou datation (C14, phases La Tène, etc.) ; risque de **mojibake** si ré-encodage incorrect (ex. « La TÃ¨ne » pour « La Tène ») |
| `g` | texte | 100 % | 26 | **Description contextuelle** — comblements, fossés, céramique, etc. |
| `h` | texte | 100 % | 15 | **Détail mobilier / contexte** — céramique, structures, géomorphologie |

*La correspondance exacte colonne ↔ sémantique doit être validée avec la documentation AFEAF ou le producteur du shapefile.*

---

## 3. Modèle de données

- **Granularité** : **une ligne = un segment / une entité linéaire** (ou un enregistrement attributaire lié à une polyligne), identifiée par **`id`**.
- **Cardinalité** : **1 ligne par `id`** (pas de duplication dans la table).
- **Dépendances** : en usage SIG standard, ce DBF est lié à un **.shp** (géométrie) — sans ce fichier, seules les **informations attributaires** sont exploitables ; les coordonnées ne sont **pas** dans le DBF.
- **Champs dérivés recommandés** après ingestion : `pays`, `departement`, `commune`, `lieu_dit`, `categorie_source`, `chrono_texte`, `description`, `detail_mobilier` (renommage explicite depuis a–h une fois la sémantique figée).

---

## 4. Qualité

**Points positifs**

- **Remplissage complet** : aucune valeur nulle sur les 9 colonnes.
- **Diversité locale** : plusieurs communes et lieux-dits — intérêt pour la **fine spatialisation** une fois joint à la géométrie.
- **Richesse textuelle** : champs `g` et `h` portent l’essentiel du **détail archéologique** exploitable pour classification et confiance.

**Problèmes et risques**

1. **Noms de colonnes opaques** (a–h) — risque d’erreur de mapping sans métadonnée producteur.
2. **Encodage** : fichier déclaré **latin-1** ; certains échantillons montrent des séquences typiques d’**UTF-8 mal lu en Latin-1** → normaliser en **UTF-8** après contrôle visuel.
3. **Très faible volumétrie** (27) : toute règle statistique ou carte de densité sera **non représentative**.
4. **Absence de géométrie dans l’analyse** : sans .shp, pas de validation spatiale ni de projection dans ce document.

**Synthèse** : qualité **attributaire bonne** ; qualité **interopérable** conditionnée à la **récupération de la géométrie** et au **décodage des libellés**.

---

## 5. Mapping BaseFerRhin

| Référentiel | Fichier | Usage |
|-------------|---------|--------|
| Types de sites | [`data/reference/types_sites.json`](../../reference/types_sites.json) | Mapper `e` (« habitat » → `HABITAT`), indices → `HABITAT` ou code **indéterminé** selon règle métier ; enrichir via mots-clés dans `g`/`h` (fossé, cabane, céramique → indices d’`HABITAT`, `NECROPOLE`, etc.) |
| Périodes | [`data/reference/periodes.json`](../../reference/periodes.json) | Parser `f` (C14, « La Tène », Ha/LT) via `patterns_fr` / intervalles dates si extractibles |
| Toponymes FR ⟷ DE | [`data/reference/toponymes_fr_de.json`](../../reference/toponymes_fr_de.json) | Normaliser **communes** alsaciennes et variantes pour appariement avec d’autres couches (CAG, EA-FR, ArkeoGIS) |

---

## 6. Stratégie d’ingestion

1. **Charger le DBF** avec bibliothèque adaptée (`dbfread`, `geopandas` + shapefile associé, ou `pandas` via conversion) en respectant **latin-1** ; vérifier visuellement quelques lignes pour **mojibake**.
2. **Joindre la géométrie** si le fichier `.shp` / `.gpkg` correspondant est disponible ; sinon, marquer les enregistrements comme **sans coordonnées** dans l’export intermédiaire.
3. **Renommer** a–h vers des noms métier une fois validé le dictionnaire de champs (ou conserver a–h + table de correspondance en configuration).
4. **Extraire chronologie** : regex sur dates BP/BC, phases « La Tène », « Hallstatt », etc., croisement avec `periodes.json`.
5. **Classifier le type de site** : règle prioritaire sur `e`, puis affinage par NLP léger / mots-clés sur `g` et `h` vers les codes `types_sites.json`.
6. **Apparier** aux sites BaseFerRhin existants par **commune + lieu-dit** et, si géométrie présente, par **proximité buffer** (ex. 100–250 m le long de la ligne).

---

## 7. Limites

- **Échantillon minuscule** : ne pas utiliser seul pour des indicateurs régionaux.
- **Dépendance géométrique** : valeur patrimoniale pleine seulement avec **tracés linéaires** alignés sur le terrain.
- **Sémantique implicite** : sans fiche de métadonnées AFEAF, le mapping des colonnes **a–h** reste **hypothétique** et doit être **versionné** dans le pipeline.
- **Bilingue / graphies** : lieux-dits et termes techniques peuvent nécessiter harmonisation avec `toponymes_fr_de.json` pour les zones frontalières ou bilingues.

---

*Document aligné sur `data/analysis/2026_afeaf_lineaire/metadata.json`.*
