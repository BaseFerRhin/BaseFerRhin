# CONTEXTE
Tu es un assistant expert en archéologie protohistorique européenne, data engineering et normalisation de bases patrimoniales.

Je souhaite construire un inventaire normalisé des sites de l'âge du Fer couvrant :
- Alsace (France)
- Bade-Wurtemberg (Allemagne)
- Canton de Bâle (Bâle-Ville et Bâle-Campagne, Suisse)

Les données proviennent de sources hétérogènes :
- cartes de répartition (images, PDF, SIG)
- inventaires textuels (PDF, publications, rapports)
- fichiers tabulaires (Excel, CSV)

# OBJECTIF
Créer une base de données unifiée, structurée et exploitable permettant :
- analyse spatiale
- comparaison inter-régionale
- enrichissement progressif

# LIVRABLES ATTENDUS
1. Un modèle de données normalisé (schéma)
2. Un pipeline de transformation (ETL)
3. Un exemple de dataset consolidé
4. Des fonctions de nettoyage et géocodage
5. Une documentation claire

# 1. MODELE DE DONNEES
Propose un schéma structuré avec les champs suivants (minimum) :

## Identification
- site_id (unique, stable)
- nom_site
- variantes_nom

## Localisation
- pays
- region_admin (Alsace / Baden-Württemberg / Basel-Stadt / Basel-Landschaft)
- commune
- latitude
- longitude
- precision_localisation (exact / approx / centroid)

## Contexte archéologique
- periode (Hallstatt / La Tène / indéterminé)
- type_site (habitat, oppidum, nécropole, dépôt, sanctuaire, etc.)
- description
- surface_estimee
- altitude

## Chronologie
- datation_debut
- datation_fin
- methode_datation (typologie, C14, etc.)

## Sources
- source_principale
- type_source (carte, texte, tableur)
- reference_bibliographique
- url / archive

## Qualité des données
- niveau_confiance (faible / moyen / élevé)
- commentaire_qualite

# 2. PIPELINE ETL
Décris et implémente en Python un pipeline modulaire :

## Étapes :
1. ingestion des données (PDF, images, CSV)
2. extraction :
   - OCR si nécessaire
   - parsing texte
3. normalisation :
   - noms de lieux
   - périodes
   - types de sites
4. déduplication :
   - fuzzy matching sur noms + coordonnées
5. géocodage :
   - via Nominatim / BAN / API open data
6. validation
7. export (GeoJSON + CSV + SQLite)

# 3. NORMALISATION
Crée :
- un dictionnaire de correspondance :
  - "oppidum", "fortification", "enceinte" → catégorie standard
- une harmonisation des langues :
  - français / allemand

# 4. CODE ATTENDU
Génère :
- une structure de projet Python claire :