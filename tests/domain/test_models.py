import pytest
from pydantic import ValidationError

from src.domain.models import (
    NiveauConfiance,
    Pays,
    Periode,
    PrecisionLocalisation,
    TypeSite,
    PhaseOccupation,
    RawRecord,
    Site,
    Source,
)


class TestTypeSiteEnum:
    def test_all_nine_values(self):
        assert len(TypeSite) == 9

    def test_oppidum_value(self):
        assert TypeSite.OPPIDUM.value == "oppidum"


class TestPeriodeEnum:
    def test_hallstatt_serialization(self):
        assert Periode.HALLSTATT.value == "Hallstatt"

    def test_four_values(self):
        assert len(Periode) == 4


class TestPhaseOccupation:
    def test_valid_phase(self):
        phase = PhaseOccupation(
            phase_id="P1", site_id="S1", periode=Periode.HALLSTATT, sous_periode="Ha D1"
        )
        assert phase.periode == Periode.HALLSTATT
        assert phase.sous_periode == "Ha D1"

    def test_sub_period_inconsistency_raises(self):
        with pytest.raises(ValidationError, match="incompatible"):
            PhaseOccupation(
                phase_id="P1", site_id="S1", periode=Periode.HALLSTATT, sous_periode="LT B2"
            )

    def test_no_sub_period_ok(self):
        phase = PhaseOccupation(phase_id="P1", site_id="S1", periode=Periode.INDETERMINE)
        assert phase.sous_periode is None


class TestSource:
    def test_gallica_source(self):
        source = Source(
            source_id="SRC1",
            site_id="S1",
            reference="CAG 67, p.42",
            type_source="gallica_cag",
            ark_gallica="ark:/12148/bd6t542071728",
            page_gallica=42,
            confiance_ocr=0.85,
        )
        assert source.ark_gallica == "ark:/12148/bd6t542071728"
        assert source.confiance_ocr == 0.85

    def test_confiance_ocr_out_of_range(self):
        with pytest.raises(ValidationError):
            Source(
                source_id="SRC1",
                site_id="S1",
                reference="test",
                confiance_ocr=1.5,
            )


class TestSite:
    def _make_site(self, **overrides):
        defaults = {
            "site_id": "CAG67-BRUMATH-001",
            "nom_site": "Habitat hallstattien de Brumath",
            "pays": Pays.FR,
            "region_admin": "Alsace",
            "commune": "Brumath",
            "precision_localisation": PrecisionLocalisation.APPROX,
            "type_site": TypeSite.HABITAT,
        }
        defaults.update(overrides)
        return Site(**defaults)

    def test_valid_creation(self):
        site = self._make_site()
        assert site.site_id == "CAG67-BRUMATH-001"
        data = site.model_dump(mode="json")
        assert data["pays"] == "FR"

    def test_missing_commune_raises(self):
        with pytest.raises(ValidationError):
            Site(
                site_id="S1",
                nom_site="Test",
                pays=Pays.FR,
                region_admin="Alsace",
                precision_localisation=PrecisionLocalisation.EXACT,
                type_site=TypeSite.HABITAT,
            )

    def test_invalid_pays_raises(self):
        with pytest.raises(ValidationError):
            self._make_site(pays="IT")

    def test_multi_phase_site(self):
        site = self._make_site(
            phases=[
                PhaseOccupation(
                    phase_id="P1", site_id="S1",
                    periode=Periode.HALLSTATT, sous_periode="Ha D3",
                ),
                PhaseOccupation(
                    phase_id="P2", site_id="S1",
                    periode=Periode.LA_TENE, sous_periode="LT A",
                ),
            ]
        )
        assert len(site.phases) == 2
        assert site.phases[0].periode == Periode.HALLSTATT
        assert site.phases[1].periode == Periode.LA_TENE

    def test_multi_source_site(self):
        site = self._make_site(
            sources=[
                Source(source_id="SRC1", site_id="S1", reference="CAG 67"),
                Source(source_id="SRC2", site_id="S1", reference="CAAH 2003"),
            ]
        )
        assert len(site.sources) == 2

    def test_auto_timestamps(self):
        site = self._make_site()
        assert site.date_creation is not None
        assert site.date_maj is not None

    def test_json_serialization(self):
        site = self._make_site()
        json_str = site.model_dump_json()
        assert "CAG67-BRUMATH-001" in json_str


class TestRawRecord:
    def test_creation(self):
        record = RawRecord(
            commune="Brumath",
            type_mention="habitat",
            extraction_method="gallica_ocr",
        )
        assert record.commune == "Brumath"
        assert record.extraction_method == "gallica_ocr"
