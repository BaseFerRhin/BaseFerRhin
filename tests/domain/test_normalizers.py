from src.domain.models.enums import Periode, TypeSite
from src.domain.normalizers import PeriodeNormalizer, ToponymeNormalizer, TypeSiteNormalizer


class TestTypeSiteNormalizer:
    def setup_method(self):
        self.norm = TypeSiteNormalizer()

    def test_french_alias_oppidum(self):
        assert self.norm.normalize("fortification") == TypeSite.OPPIDUM

    def test_french_alias_fortification_de_hauteur(self):
        assert self.norm.normalize("fortification de hauteur") == TypeSite.OPPIDUM

    def test_german_alias_hohensiedlung(self):
        assert self.norm.normalize("Höhensiedlung") == TypeSite.OPPIDUM

    def test_german_graberfeld_necropole(self):
        assert self.norm.normalize("Gräberfeld") == TypeSite.NECROPOLE

    def test_case_insensitive(self):
        assert self.norm.normalize("HABITAT") == TypeSite.HABITAT

    def test_unknown_fallback(self):
        assert self.norm.normalize("Bodenmarkierung") == TypeSite.INDETERMINE
        assert "Bodenmarkierung" in self.norm.unrecognized_terms

    def test_substring_match(self):
        assert self.norm.normalize("grand habitat ouvert du Hallstatt") == TypeSite.HABITAT


class TestPeriodeNormalizer:
    def setup_method(self):
        self.norm = PeriodeNormalizer()

    def test_premier_age_du_fer(self):
        periode, sub = self.norm.normalize("premier âge du Fer")
        assert periode == Periode.HALLSTATT
        assert sub is None

    def test_sub_period_extraction(self):
        periode, sub = self.norm.normalize("Ha D2-D3")
        assert periode == Periode.HALLSTATT
        assert sub == "Ha D2-D3"

    def test_german_spatlatenezeit(self):
        periode, sub = self.norm.normalize("Spätlatènezeit")
        assert periode == Periode.LA_TENE

    def test_la_tene_with_sub(self):
        periode, sub = self.norm.normalize("LT B2 ancien")
        assert periode == Periode.LA_TENE
        assert sub == "LT B2"

    def test_indetermine_fallback(self):
        periode, sub = self.norm.normalize("quelque chose sans rapport")
        assert periode == Periode.INDETERMINE
        assert sub is None


class TestToponymeNormalizer:
    def setup_method(self):
        self.norm = ToponymeNormalizer()

    def test_german_to_french(self):
        canon, variants = self.norm.normalize("Schlettstadt")
        assert canon == "Sélestat"
        assert "Schlettstadt" in variants

    def test_historical_name(self):
        canon, variants = self.norm.normalize("Brocomagus")
        assert canon == "Brumath"
        assert "Brocomagus" in variants

    def test_already_canonical(self):
        canon, variants = self.norm.normalize("Strasbourg")
        assert canon == "Strasbourg"
        assert variants == []

    def test_unknown_toponym_passthrough(self):
        canon, variants = self.norm.normalize("VillageInconnu")
        assert canon == "VillageInconnu"
        assert variants == []
