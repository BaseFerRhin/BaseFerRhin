from src.domain.models.enums import Periode
from src.domain.models.phase import PhaseOccupation
from src.domain.validators import validate_chronology, validate_coordinates
from src.infrastructure.geocoding.base import wgs84_to_l93


class TestChronologyValidator:
    def test_date_inversion(self):
        phase = PhaseOccupation(
            phase_id="P1", site_id="S1",
            periode=Periode.LA_TENE,
            datation_debut=-300, datation_fin=-500,
        )
        warnings = validate_chronology(phase)
        messages = [w.message for w in warnings]
        assert any("datation_debut > datation_fin" in m for m in messages)

    def test_valid_dates_no_warning(self):
        phase = PhaseOccupation(
            phase_id="P1", site_id="S1",
            periode=Periode.HALLSTATT,
            datation_debut=-700, datation_fin=-500,
        )
        warnings = validate_chronology(phase)
        assert len(warnings) == 0

    def test_date_outside_period_range(self):
        phase = PhaseOccupation(
            phase_id="P1", site_id="S1",
            periode=Periode.HALLSTATT,
            datation_debut=-900,
        )
        warnings = validate_chronology(phase)
        assert len(warnings) == 1
        assert "antérieure" in warnings[0].message

    def test_sub_period_mismatch(self):
        phase = PhaseOccupation(
            phase_id="P1", site_id="S1",
            periode=Periode.LA_TENE,
            sous_periode="LT C1",
        )
        warnings = validate_chronology(phase)
        assert len(warnings) == 0

    def test_sub_period_ha_under_la_tene_blocked_by_model(self):
        """Sub-period mismatch is caught at model level (Pydantic validator)."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="incompatible"):
            PhaseOccupation(
                phase_id="P1", site_id="S1",
                periode=Periode.LA_TENE,
                sous_periode="Ha D1",
            )


class TestGeoValidator:
    def test_coordinates_in_region(self):
        x, y = wgs84_to_l93(7.75, 48.58)
        warnings = validate_coordinates(x, y, "Alsace")
        assert len(warnings) == 0

    def test_coordinates_outside_region(self):
        x, y = wgs84_to_l93(7.75, 52.0)
        warnings = validate_coordinates(x, y, "Alsace")
        assert len(warnings) == 1
        assert "y_l93" in warnings[0].field

    def test_none_coordinates_no_warning(self):
        warnings = validate_coordinates(None, None)
        assert len(warnings) == 0

    def test_x_outside(self):
        x, y = wgs84_to_l93(12.0, 48.0)
        warnings = validate_coordinates(x, y)
        assert any("x_l93" in w.field for w in warnings)
