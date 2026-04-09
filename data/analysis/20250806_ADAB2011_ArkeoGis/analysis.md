# Analyse — `20250806_ADAB2011_ArkeoGis.csv`

Document d’analyse pour l’export ArkeoGIS fusionnant deux extraits de l’inventaire archéologique **ADAB-2011** (Nordbaden et Südbaden, Allemagne). Les métriques proviennent du fichier `metadata.json` associé et d’un contrôle statistique sur `data/input/20250806_ADAB2011_ArkeoGis.csv` (656 lignes de données, séparateur `;`, UTF-8).

---

## 1. Vue d’ensemble

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `20250806_ADAB2011_ArkeoGis.csv` (chemin canonique : `data/input/`) |
| **Source** | Export **ArkeoGIS**, agrégation de **2 bases** : « Extrait de l'inventaire archéologique Nordbaden- ADAB-2011 » (465 lignes) et « Extrait de l'inventaire archéologique Südbaden-ADAB-2011 » (191 lignes) |
| **Volume** | **656** lignes, **23** colonnes, **655** sites uniques (`SITE_AKG_ID`) |
| **Géographie** | Nordbaden + Südbaden (DE) ; lat. **48,02–48,78° N**, long. **7,58–8,28° E** ; système **EPSG:4326** |
| **Positionnement** | **81,2 %** des lignes avec `CITY_CENTROID=Oui` (coordonnées de **centroïde communal**, pas de site précis) |
| **Chronologie** | Plage numérique possible **-2200** à **1701** selon les champs période ; **71,2 %** des lignes (**467**) avec périodes **« Indéterminé »** ; **134** lignes (**28,8 %**) avec intervalles datés non entièrement indéterminés (dont sous-ensemble interprétable comme âge du Fer selon filtrage) |
| **Confiance globale** | **MOYENNE** (`MEDIUM`) : géolocalisation souvent générique, datation majoritairement floue, mais identifiants stables et champ `COMMENTS` riche |
| **Rôle projet** | Couverture volumique badoise complémentaire d’inventaires plus ciblés (ex. sélection âge du Fer) ; nécessite **filtrage**, **parsing des commentaires** et **gestion des centroïdes** avant usage analytique fin |

---

## 2. Schéma détaillé des colonnes

*Types inférés par le générateur de métadonnées (pandas). **Remplissage** = part de valeurs non nulles / non NA.*

| Colonne | Type | Remplissage | Nb. valeurs uniques | Valeurs dominantes (aperçu) |
|---------|------|-------------|---------------------|------------------------------|
| `SITE_AKG_ID` | entier | 100 % | 655 | Identifiant ArkeoGIS global (presque 1 valeur par site) |
| `DATABASE_NAME` | texte | 100 % | 2 | Nordbaden ADAB-2011 (~465) ; Südbaden ADAB-2011 (~191) |
| `SITE_SOURCE_ID` | texte | 100 % | 655 | Codes type `BW_*` (inventaire régional) |
| `SITE_NAME` | texte | 100 % | 315 | Libellés localisés ; **201** valeurs avec guillemets mal formés (`""""`) |
| `MAIN_CITY_NAME` | texte | 100 % | 62 | Communes (allemand) |
| `GEONAME_ID` | flottant | **0 %** | 0 | Toujours vide |
| `PROJECTION_SYSTEM` | entier | 100 % | 1 | `4326` |
| `LONGITUDE` | flottant | 100 % | 655 | ~7,58–8,28° E |
| `LATITUDE` | flottant | 100 % | 654 | ~48,02–48,78° N |
| `ALTITUDE` | flottant | **0 %** | 0 | Toujours vide |
| `CITY_CENTROID` | texte | 100 % | 2 | **Oui** (~533, **81,2 %**) ; **Non** (~123) |
| `STATE_OF_KNOWLEDGE` | texte | 100 % | 2 | **Non renseigné** (~652) ; **Prospecté aérien** (4) |
| `OCCUPATION` | texte | 100 % | 1 | **Non renseigné** (100 %) |
| `STARTING_PERIOD` | texte | 100 % | 10 | Souvent **Indéterminé** ; sinon intervalles type `-2200:-26`, `-800:-461`, etc. |
| `ENDING_PERIOD` | texte | 100 % | 14 | Même logique que début de période |
| `CARAC_NAME` | texte | 100 % | 5 | **Immobilier** (~473) ; **Mobilier** (~69) ; **Paysage** (~59) ; **Production** (~54) ; **Analyses** (1) |
| `CARAC_LVL1` | texte | 100 % | **17** | **Funéraire** (~192) ; **Habitat** (~178) ; **Charbon** (~45) ; **Autres** (~39) ; **Structure agraire** (~38) ; **Enceinte** (~30) ; **Indéterminé** (~30) ; **Céramique** (~28) ; etc. |
| `CARAC_LVL2` | texte | **65,1 %** | 16 | NA (~229) ; **Non renseigné** (~181) ; **Groupé** (~149) ; **Fossé** (~42) ; **Voie** (~19) ; … |
| `CARAC_LVL3` | texte | **30,2 %** | 13 | NA (~458) ; **Monument funéraire** (~176) ; **Enclos** (~7) ; **Source** (~2) ; … |
| `CARAC_LVL4` | texte | **0,5 %** | 2 | Presque toujours NA ; rares : **Inhumation**, **Canalisation** |
| `CARAC_EXP` | texte | 100 % | 1 | **Non** |
| `BIBLIOGRAPHY` | texte | 100 % | 605 | Références sèches du type `-- # AKTENZEICHEN : L7314/065-01` |
| `COMMENTS` | texte | 100 % | 209 | Métadonnées **structurées en allemand** (voir §4 et §6) |

---

## 3. Analyse du modèle de données

### Granularité site / ligne

Le modèle ArkeoGIS attendu (« une ligne = une caractéristique de site ») est ici **presque trivial** : en moyenne **1,0** ligne par site, avec un maximum de **2** lignes pour un même `SITE_AKG_ID`. En pratique, **chaque site n’apporte qu’une ou deux entrées** dans cet export : pas de explosion combinatoire multi-caractéristiques comme sur d’autres exports.

Clé primaire logique côté ArkeoGIS : **`SITE_AKG_ID`** (couplée à `SITE_SOURCE_ID` pour traçabilité vers l’inventaire BW).

### Hiérarchie `CARAC_*`

- **`CARAC_NAME`** distingue surtout l’ancrage patrimonial (Immobilier dominant, Mobilier, Paysage, Production, Analyses) — niveau **macro** non directement équivalent au typage archéologique « type de site » BaseFerRhin.
- **`CARAC_LVL1`** compte **17** modalités : elles structurent l’essentiel de la sémantique (Habitat, Funéraire, Enceinte, Circulation, Structure agraire, Formation superficielle, Charbon, Indéterminé, Céramique, Métal, etc.). C’est le **premier niveau exploitable** pour un mapping vers des types normalisés, avec recoupement nécessaire sur `CARAC_LVL2` / `CARAC_LVL3`.
- **`CARAC_LVL2`** : **34,9 %** de valeurs nulles ; quand renseigné : *Groupé*, *Non renseigné*, *Fossé*, *Voie*, *Nécropole*, etc.
- **`CARAC_LVL3`** : **69,8 %** nul ; quand renseigné : *Monument funéraire*, *Enclos*, *Source* notamment.
- **`CARAC_LVL4`** : **99,5 %** nul — niveau quasi absent dans cet extract.
- **`CARAC_EXP`** : constant à « Non » — pas d’indicateur d’explicitation supplémentaire ici.

### Champs peu informatifs dans cet export

- **`STATE_OF_KNOWLEDGE`** : quasi exclusivement « Non renseigné », sauf **4** « Prospecté aérien ».
- **`OCCUPATION`** : sans variance (100 % « Non renseigné »).
- **`ALTITUDE`** et **`GEONAME_ID`** : entièrement vides.

La **charge sémantique utile** pour affiner au-delà de `CARAC_LVL1` repose donc fortement sur **`COMMENTS`** (et secondairement sur les libellés allemands dans ce champ).

---

## 4. Analyse de qualité

### Points positifs

- **Coordonnées** : toujours présentes (100 %), référence spatiale cohérente (WGS84).
- **Identifiants** : `SITE_AKG_ID` / `SITE_SOURCE_ID` stables et presque bijectifs aux sites.
- **`BIBLIOGRAPHY`** : toujours rempli — utile comme **clé administrative** (numéro de dossier / Aktenzeichen), moins comme synthèse bibliographique narrative.
- **`COMMENTS`** : contient des champs allemands **répétitifs et parsables** (`LISTENTEXT`, `BEGRUENDUNG`, `GENAUIGK_T`, `DAT_GROB`, `DAT_FEIN`, `TYP_GROB`, `TYP_FEIN`, `AUTRES`) — **très utile** pour préciser type chronologique grossier, type fonctionnel fin, et **tolérance de localisation** (ex. *mit 20 m Toleranz*, *bis zu 200m*).

### Problèmes et biais

1. **Guillemets malformés dans `SITE_NAME`** : **201** valeurs affectées (séquences `""""` issues d’un échappement CSV incorrect). Risque d’affichage bruité et de clés de dédoublonnage fausses si non nettoyé.
2. **Datation** : **71,2 %** des lignes avec période **indéterminée** au sens ArkeoGIS — limite directe pour tout écran ou statistique « âge du Fer seul » sans enrichissement.
3. **Occupation et état des connaissances** : champs quasiment constants → **pas de levier qualitatif** pour filtrer la densité d’information.
4. **Altitude** : absente → pas de corrélation relief / type de site sans source externe (MNT).
5. **Centroïdes** : **81,2 %** `CITY_CENTROID=Oui` → les analyses spatiales (clustering, distance au Rhin, densité) doivent traiter ces points comme **localisations grossières** (biais vers le centre administratif).
6. **Diversité des `COMMENTS`** : 209 combinaisons uniques pour 656 lignes — beaucoup de répétition mais extraction **manuelle impossible** à l’échelle ; un **parseur structuré** est nécessaire pour exploiter `DAT_FEIN` / `TYP_FEIN` de façon systématique.

**Synthèse** : qualité **MOYENNE** — exploitable pour inventaire régional et enrichissement croisé, **insuffisante seule** pour une cartographie « haute précision » chrono-spatiale de l’âge du Fer.

---

## 5. Mapping vers le modèle BaseFerRhin

Les tables de référence du dépôt à mobiliser :

| Référentiel | Fichier | Usage pour ADAB2011 |
|-------------|---------|---------------------|
| Types de sites (alias FR/DE) | [`data/reference/types_sites.json`](../../reference/types_sites.json) | Correspondance **Habitat / Funéraire / Enceinte / Voie / production** → codes canoniques (`HABITAT`, `NECROPOLE`, `TUMULUS`, `OPPIDUM`, `VOIE`, `ATELIER`, `DEPOT`, `SANCTUAIRE`, …) via les listes **`aliases.de`** (ex. *Siedlung*, *Grabhügel*, *Hügelgrab*, *Ringwall*, *Weg*, *Straße*, *Hortfund*…) et **`aliases.fr`** pour cohérence avec le reste du corpus |
| Périodes | [`data/reference/periodes.json`](../../reference/periodes.json) | Normalisation des intervalles et libellés vers **Hallstatt**, **La Tène**, **TRANSITION** ; appui sur **`patterns_de`** (*Hallstattzeit*, *Latènezeit*, *Ältere/Jüngere Eisenzeit*, *Metallzeiten* comme fourchette large) et sur **`sub_period_regex`** pour phases Ha/LT quand présentes dans le texte |
| Toponymes FR ⟷ DE | [`data/reference/toponymes_fr_de.json`](../../reference/toponymes_fr_de.json) | Utile surtout pour sites **proches de la rive rhénane** (ex. *Breisach am Rhein*, *Basel*) ; la majorité des `MAIN_CITY_NAME` sont des communes **exclusivement allemandes** non listées — conserver le nom allemand comme canonique avec **option** d’enrichissement manuel ou futur dictionnaire BW/DE |

### Correspondances indicatives `CARAC_LVL1` → `types_sites.json`

| `CARAC_LVL1` (extrait) | Piste vers alias / code |
|------------------------|-------------------------|
| Habitat | `HABITAT` (*Siedlung*, structures d’habitat) |
| Funéraire | `NECROPOLE`, `TUMULUS` selon `CARAC_LVL2`/`LVL3` (*Monument funéraire*, *Grabhügel*) |
| Enceinte | `OPPIDUM` / fortifications (*Befestigung*, *Ringwall* si présent dans COMMENTS) |
| Circulation | `VOIE` |
| Structure agraire, Formation superficielle | souvent **indéterminé** ou hors périmètre Fer — documenter comme `INDETERMINE` ou exclure par règle métier |
| Charbon, Céramique, Métal, Lithique, Os, Dépôt | `ATELIER`, `DEPOT` ou activité annexes — affiner avec `TYP_*` allemand dans `COMMENTS` |
| Rituel | `SANCTUAIRE` si contexte cultuel avéré, sinon prudence |
| Indéterminé | type site **indéterminé** ; tenter rescousse via **`TYP_FEIN` / `TYP_GROB`** parsés |

### Cas particulier : enrichissement par **`COMMENTS`**

Le champ n’est pas une note libre : il encapsule une **micro-fiche** allemande. Pour le modèle BaseFerRhin :

- **`DAT_FEIN`** : ex. *Metallzeiten*, *unbestimmt* → croiser avec `periodes.json` (les *Metallzeiten* couvrent une large plage : ne pas confondre avec Ha/LT sans autre indice).
- **`TYP_FEIN`** : ex. *Siedlung*, *Grabhügel*, *Ort, Stadtbild (Luftbild)* → mapping direct vers alias **DE** de `types_sites.json` (*Siedlung* → habitat ; *Grabhügel* → tumulus/nécropole tumulaire).
- **`GENAUIGK_T`** : alimenter un **score de confiance géographique** (20 m vs 200 m vs non précisé) distinct du simple flag `CITY_CENTROID`.

---

## 6. Stratégie d’ingestion (6 étapes)

1. **Lecture et normalisation CSV** : `sep=";"`, UTF-8 ; normaliser les guillemets et espaces dans `SITE_NAME` ; valider les couples (lat, lon) dans l’emprise documentée.
2. **Attribution confiance spatiale** : si `CITY_CENTROID=Oui` → marquer confiance **basse** pour la position ; si `COMMENTS` contient `GENAUIGK_T` avec tolérance explicite, **surcharger** ou compléter par une incertitude en mètres (20 / 200).
3. **Parsing structuré de `COMMENTS`** : extraire paires clé/valeur (`DAT_GROB`, `DAT_FEIN`, `TYP_GROB`, `TYP_FEIN`, …) via regex ou split sur `#` ; produire colonnes techniques dérivées pour la suite du pipeline.
4. **Classification type de site** : règles en cascade — (a) `TYP_FEIN` / `TYP_GROB` allemands contre `types_sites.json` → `aliases.de` ; (b) sinon `CARAC_LVL3` + `CARAC_LVL2` + `CARAC_LVL1` ; (c) défaut **indéterminé**. Exemples cibles : *Metallzeiten* + *Siedlung* → habitat + période métallique large à affiner ; *Grabhügel* → tumulus / nécropole selon modèle cible.
5. **Normalisation chronologique** : si `STARTING_PERIOD` / `ENDING_PERIOD` ≠ Indéterminé, parser les bornes numériques et intersecter avec les plages **Hallstatt / La Tène / TRANSITION** dans `periodes.json` ; sinon utiliser `DAT_FEIN` parsé pour un **étiquetage qualitatif** (sans forcer une fausse précision).
6. **Dédoublonnage et rattachement** : clé primaire logique `SITE_AKG_ID` ; croiser avec autres sources (ex. Loup Bernard, CAG) par **proximité spatiale + nom normalisé** ; conserver `DATABASE_NAME` et `SITE_SOURCE_ID` en traçabilité ; appliquer `toponymes_fr_de.json` lorsque la commune figure au tableau de concordance.

---

## 7. Limites et précautions

- **Complétude d’inventaire** : l’ADAB est un **inventaire régional multi-périodes**, pas une sélection âge du Fer exhaustive ni représentative des densités réelles par période ; tout indicateur « part du Fer » sera **conditionné par le filtrage** appliqué.
- **Coordonnées** : même hors centroïde, les mentions **20 m** ou **jusqu’à 200 m** dans `COMMENTS` imposent une **tolérance locale 20–200 m** ; ne pas interpréter les points comme GPS de fouille sans retour aux dossiers.
- **Datation minimale** : avec **~71 %** d’indéterminés ArkeoGIS, les statistiques chronologiques doivent **expliciter le taux de non-daté** ; l’âge du Fer n’est **pas déductible** pour la majorité des lignes sans texte externe.
- **Nomenclature allemande** : les types et commentaires sont en **allemand administratif / archéologique** ; le mapping vers un modèle bilingue ou francophone introduit une **couche d’interprétation** — documenter les règles et les cas limites (*Ort, Stadtbild (Luftbild)* vs site archéologique identifié, etc.).
- **BIBLIOGRAPHY** : format **référentiel de gestion** plutôt que référence scientifique lisible ; pour les publications, prévoir des sources complémentaires.
- **Biases spatiaux** : forte concentration de centroïdes communaux → risque d’**artefacts de densité** le long des chefs-lieux ; pour les analyses paysagères, privilégier les **533** vs **123** lignes selon `CITY_CENTROID` ou pondérer.

---

*Document généré pour le dossier `data/analysis/20250806_ADAB2011_ArkeoGis/` — aligné sur `metadata.json` du même répertoire.*
