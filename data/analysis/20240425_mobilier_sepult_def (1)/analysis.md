# Analyse — Mobilier des sépultures (définition détaillée)

## 1. Vue d'ensemble

| Élément | Détail |
|--------|--------|
| **Fichier** | `20240425_mobilier_sepult_def (1).ods` |
| **Chemin source** | `data/input/20240425_mobilier_sepult_def (1).ods` |
| **Format** | ODS (moteur `odf` / `pandas` + `odfpy` ou `calamine` selon env.) |
| **Volume** | **310 lignes**, **91 colonnes**, ~71 Ko |
| **Export métadonnées** | 2024-04-25 |
| **Contexte archéologique** | **Sépultures** (inhumations, doubles/triples) avec **inventaire détaillé du mobilier** : céramique (pots, écuelles, vases miniatures…), parure (fibules, bracelets, perles, torque…), armes et harnachement ponctuels, matières (ambre, verre, roche noire). **Typologie fine** des pratiques funéraires (position du corps, décomposition, offrandes). Région couverte : **Lorraine / Alsace du Nord** (échantillon de communes : Woippy, Duttlenheim, Sainte-Croix-en-Plaine…). Coordonnées **Lambert-93 complètes** (0 % manquant sur X/Y). |

**Projet cible :** BaseFerRhin.

---

## 2. Schéma des colonnes (colonnes clés)

### Identification locale

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Commune` | object | 100 % | Woippy, Duttlenheim |
| `lieu-dit` | object | 100 % | Zac des Chiloux, Site 1.3 |
| `N° enclos` | object | ~92,6 % | E27, HE, E4 |
| `N° Sep` | object | ~99,4 % | 188, 191 (quasi-identifiant sépulture) |
| `TR/FEN` | object | ~21,6 % | peu renseigné |

### Définition de la sépulture

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `type sép` | object | 100 % | inhumation, tombe double, triple |
| `Type de fosse et dépôt funéraire` | object | ~79,4 % | tombe à double coffrage, fosse circulaire |
| `Profil`, `Recoupement`, `Localisation vase ossuaire…` | object | variable | contexte stratigraphique |
| `Position corps`, `Décomposition`, `Couverture` | object | variable | pratiques funéraires |
| `Position céramique`, `Posiiton métal` | object | variable | faute : « Posiiton » |

### Mobilier (aperçu)

Comptages ou présence sur : `Pot`, `Couvercle`, `Gobelet`, `Coupe`, `Tasse`, `Ecuelle`, `Jatte`, `Vase miniature`… ; parure `AC Fibule`, `AC Bracelet`, `AC Anneau`, `AC Torque`… ; `Lithique`, `Fer épée/poignard`, `Fer Char`, etc. Certaines colonnes **quasi vides** (`Fer Brassard`, `AC Vaisselle` : 100 % NA selon métadonnées).

### Anthropologie et chrono

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `comptage pondéré/ NMI` | int64 | 100 % | 1, 3, 7 |
| `NMI anthropo` | object | ~31,6 % | 1, 2 |
| `chrono` | object | 100 % | Ha D3, LT A, Ha D-LT A ? |
| `Genre` | object | 100 % | Féminin, Masculin, Indéterminé |
| `Remarques` | object | ~39 % | mobilier exceptionnel, datations typo |

### Coordonnées

| Colonne | Type | Taux remplissage | Exemples |
|---------|------|------------------|----------|
| `Coordonnées x (Lambert 93)` | float64 | 100 % | 929861, 1038067 |
| `Coordonnées y (Lambert 93)` | float64 | 100 % | 6899179, 6834890 |

**Qualité globale :** taux de remplissage moyen ~32,1 % ; colonnes **`Fer Brassard`** et **`AC Vaisselle`** entièrement vides ; **`Roche noire Brassard`** quasi vide.

---

## 3. Modèle de données (grain)

- **Une ligne = une sépulture** (ou un dépôt funéraire compté comme une unité), identifiée de façon opérationnelle par **`Commune` + `lieu-dit` + `N° Sep`**.
- **Plusieurs lignes** peuvent appartenir au **même site** (mêmes coordonnées ou même ZAC) : pour BaseFerRhin au niveau **site**, il faut **agrégation**.

---

## 4. Qualité

| Aspect | Constat |
|--------|---------|
| **Coordonnées** | L93 **complètes** ; étendue X/Y compatible avec nord-est français (dont Lorraine). |
| **Chronologie** | Colonne `chrono` systématique ; formulations Ha/LT à parser. |
| **Typographie** | `Posiiton métal`, `Offande secondaire` (typo « Offande »), espaces en fin de certains noms de colonnes. |
| **Colonnes vides** | À exclure du mapping ou à ignorer en import. |
| **Confiance** | LOW (métadonnées automatiques). |

---

## 5. Mapping vers BaseFerRhin

| Cible | Source |
|-------|--------|
| `nom_site` | `lieu-dit` (prioritaire) ou `Commune` + précision |
| `commune` | `Commune` | `toponymes_fr_de.json` |
| `pays` | `FR` (déductible du contexte géographique ; à confirmer ligne à ligne si transfrontalier) |
| `type_site` | **NECROPOLE** (inhumation, ensemble funéraire) |
| `x_l93`, `y_l93` | `Coordonnées x (Lambert 93)`, `Coordonnées y (Lambert 93)` |
| `periode` / `sous_periode` | Parser `chrono` via `periodes.json` |
| `notes` / extension | Résumé comptages céramique / parure, `Remarques` |

**Granularité :** conserver une **table `sepultures_mobilier.csv`** au grain 310 lignes pour la recherche ; n’envoyer vers `sites.csv` qu’après **dedup spatial + toponymique**.

---

## 6. Stratégie d’ingestion

1. **Lecture ODS** : `pd.read_excel(..., engine="odf")` (dépendance `odfpy`) ou conversion CSV intermédiaire.
2. **Renommage** colonnes (typos, espaces).
3. **Filtrage** colonnes 100 % NA.
4. **Validation L93** (plages France / voisinage).
5. **Classification** période depuis `chrono` ; type_site = nécropole.
6. **Agrégation par site** : cluster par coords arrondies ou par commune+lieu-dit.
7. **Déduplication** vs `sites.csv` (distance + nom).
8. **Export** sites + optionnel table détail sépultures.

---

## 7. Limites

- **310 points** peuvent représenter **moins de 310 sites** (même nécropole) : risque de **suroccupation** cartographique si pas d’agrégation.
- **Mobilier** : matrice très large et creuse — inadaptée au schéma minimal **sites** sans table annexe.
- **Genre / NMI** : utiles pour études anthropologiques, pas pour le noyau géo du référentiel site.
- **Unicité `N° Sep`** : probablement **locale au chantier** ; ne pas utiliser comme ID global seul.

---

*Document basé sur `metadata.json` et `data/reference/`.*
