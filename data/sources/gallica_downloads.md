# Sources Gallica — Téléchargement manuel

## Où placer les fichiers téléchargés

```
data/sources/
├── gallica_downloads.md      ← ce fichier
├── golden_sites.csv           ← dataset de référence (déjà présent)
├── pdf/                       ← PDFs téléchargés manuellement
│   ├── CAG_67_1_Bas-Rhin.pdf
│   ├── CAG_67_2_Strasbourg.pdf
│   └── CAG_68_Haut-Rhin.pdf
└── gallica_metadata.json      ← métadonnées des documents (créé automatiquement)
```

Après téléchargement, ajoutez les PDFs dans `config.yaml` :

```yaml
sources:
  - path: data/sources/golden_sites.csv
    type: csv
  - path: data/sources/pdf/CAG_67_1_Bas-Rhin.pdf
    type: pdf
  - path: data/sources/pdf/CAG_67_2_Strasbourg.pdf
    type: pdf
  - path: data/sources/pdf/CAG_68_Haut-Rhin.pdf
    type: pdf
```

---

## 1. Carte archéologique de la Gaule (CAG) — PRIORITÉ HAUTE

Les CAG sont les références fondamentales : inventaire commune par commune de tous les sites archéologiques connus.

### CAG 67/1 — Le Bas-Rhin

- **Titre** : Carte archéologique de la Gaule. [Nouvelle série]. 67, Le Bas-Rhin
- **Auteurs** : Pascal Flotté, Matthieu Fuchs
- **Éditeur** : Académie des Inscriptions et Belles-Lettres / MSH, Paris
- **Année** : 2000
- **Pages** : ~735
- **ARK (notice)** : `ark:/12148/bd6t54207173p`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bd6t54207173p
- **Statut** : Notice bibliographique uniquement (pas numérisé en OCR sur Gallica)
- **Téléchargement** : Disponible en PDF sur le site des éditions de la MSH ou en bibliothèque

### CAG 67/2 — Strasbourg

- **Titre** : Carte archéologique de la Gaule. 67, Strasbourg
- **Auteurs** : Juliette Baudoux, Pascal Flotté, Matthieu Fuchs et al.
- **Année** : 2002
- **Pages** : ~586
- **ARK (notice)** : `ark:/12148/bd6t542071728`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bd6t542071728
- **Statut** : Notice bibliographique uniquement

### CAG 68 — Le Haut-Rhin

- **Titre** : Carte archéologique de la Gaule. [Nouvelle série]. 68, Haut-Rhin
- **Auteur** : Muriel Zehner
- **Année** : 1998
- **Pages** : ~375
- **ARK (notice)** : `ark:/12148/bd6t542071580`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bd6t542071580
- **Statut** : Notice bibliographique uniquement

---

## 2. Documents numérisés sur Gallica — IIIF disponible

Ces documents sont entièrement numérisés. Le pipeline les télécharge automatiquement via IIIF + Tesseract OCR (mais Gallica rate-limite après ~10 pages/session).

### Musée archéologique de Strasbourg — L'Alsace des origines au VIIIe siècle

- **Auteur** : Bernadette Schnitzler
- **ARK** : `12148/bpt6k33200263`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bpt6k33200263
- **PDF** : https://gallica.bnf.fr/ark:/12148/bpt6k33200263.pdf
- **Pertinence** : ★★★ — nécropoles, oppida, mobilier de l'âge du Fer en Alsace
- **Pages OCR déjà en cache** : f1–f5

### Bronzes antiques d'Alsace

- **ARK** : `12148/bpt6k1002738n`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bpt6k1002738n
- **PDF** : https://gallica.bnf.fr/ark:/12148/bpt6k1002738n.pdf
- **Pertinence** : ★★ — objets en bronze, localisations de découvertes

### L'Ancienne Alsace à table (Ch. Gérard, 2e éd.)

- **ARK** : `12148/bpt6k32151645`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bpt6k32151645
- **PDF** : https://gallica.bnf.fr/ark:/12148/bpt6k32151645.pdf
- **Pertinence** : ★ — mentions occasionnelles de sites archéologiques

### Essai statistique sur les frontières nord-est de la France

- **ARK** : `12148/bpt6k7051449q`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bpt6k7051449q
- **PDF** : https://gallica.bnf.fr/ark:/12148/bpt6k7051449q.pdf
- **Pertinence** : ★ — données topographiques et archéologiques anciennes

### Manuel d'archéologie — Archéologie celtique (Déchelette, 1913)

- **Auteur** : Joseph Déchelette
- **ARK** : `12148/bpt6k6106092j`
- **Gallica** : https://gallica.bnf.fr/ark:/12148/bpt6k6106092j
- **PDF** : https://gallica.bnf.fr/ark:/12148/bpt6k6106092j.pdf
- **Pertinence** : ★★★ — référence typologie Hallstatt, sites rhénans

---

## 3. URLs de téléchargement rapide (PDF)

Pour télécharger les PDFs dans un navigateur, cliquer sur ces liens :

| Document | Lien PDF direct |
|---|---|
| Musée archéo Strasbourg | https://gallica.bnf.fr/ark:/12148/bpt6k33200263.pdf |
| Bronzes antiques Alsace | https://gallica.bnf.fr/ark:/12148/bpt6k1002738n.pdf |
| Ancienne Alsace à table | https://gallica.bnf.fr/ark:/12148/bpt6k32151645.pdf |
| Essai statistique frontières NE | https://gallica.bnf.fr/ark:/12148/bpt6k7051449q.pdf |
| Déchelette — Archéo celtique | https://gallica.bnf.fr/ark:/12148/bpt6k6106092j.pdf |

---

## 4. Requêtes SRU pour découvrir d'autres documents

À lancer quand Gallica sera de nouveau accessible (`https://gallica.bnf.fr/SRU`) :

```
dc.title all "protohistoire" and dc.subject all "Alsace"
dc.title all "Haguenau" and dc.title all "forêt"
dc.title all "tumulus" and dc.title all "Alsace"
dc.title all "âge du fer" or dc.title all "Eisenzeit"
dc.title all "hallstatt" or dc.title all "la tène"
dc.title all "nécropole" and dc.title all "Alsace"
dc.title all "oppidum" and dc.title all "Rhin"
dc.title all "fouilles" and dc.title all "Alsace"
dc.title all "Schaeffer" and dc.title all "Haguenau"
```
