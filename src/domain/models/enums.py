from enum import Enum


class TypeSite(str, Enum):
    OPPIDUM = "oppidum"
    HABITAT = "habitat"
    NECROPOLE = "nécropole"
    DEPOT = "dépôt"
    SANCTUAIRE = "sanctuaire"
    ATELIER = "atelier"
    VOIE = "voie"
    TUMULUS = "tumulus"
    INDETERMINE = "indéterminé"


class Periode(str, Enum):
    HALLSTATT = "Hallstatt"
    LA_TENE = "La Tène"
    TRANSITION = "Hallstatt/La Tène"
    INDETERMINE = "indéterminé"


class NiveauConfiance(str, Enum):
    ELEVE = "élevé"
    MOYEN = "moyen"
    FAIBLE = "faible"


class PrecisionLocalisation(str, Enum):
    EXACT = "exact"
    APPROX = "approx"
    CENTROIDE = "centroïde"


class StatutFouille(str, Enum):
    FOUILLE = "fouille"
    PROSPECTION = "prospection"
    SIGNALEMENT = "signalement"
    ARCHIVE = "archivé"


class TypeSource(str, Enum):
    GALLICA_CAG = "gallica_cag"
    GALLICA_PERIODIQUE = "gallica_periodique"
    GALLICA_OUVRAGE = "gallica_ouvrage"
    CARTE = "carte"
    TABLEUR = "tableur"
    PUBLICATION = "publication"
    RAPPORT_FOUILLE = "rapport_fouille"


class Pays(str, Enum):
    FR = "FR"
    DE = "DE"
    CH = "CH"
