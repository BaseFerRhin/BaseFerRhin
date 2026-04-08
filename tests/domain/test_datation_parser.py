"""Tests unitaires pour le DatationParser — 10 scénarios de la spec."""

import pytest

from src.domain.normalizers.datation_parser import DatationParser, ParsedPhase


class TestDatationParser:
    def setup_method(self):
        self.parser = DatationParser()

    def test_arkeogis_range_hac(self):
        """ArkeoGIS '-800:-620' → Ha C."""
        phases = self.parser.parse("-800:-620")
        assert len(phases) == 1
        assert phases[0].sous_periode == "Ha C"
        assert phases[0].debut == -800
        assert phases[0].fin == -620

    def test_arkeogis_wide_range(self):
        """ArkeoGIS '-620:-531' → Ha D (large range)."""
        phases = self.parser.parse("-620:-531")
        assert len(phases) >= 1
        assert phases[0].periode in ("Hallstatt", "La Tène")

    def test_sub_period_range_ha_d1_lt_a(self):
        """'Ha D1 - LT A' → several phases."""
        phases = self.parser.parse("Ha D1 - LT A")
        subs = [p.sous_periode for p in phases]
        assert "Ha D1" in subs
        assert "LT A" in subs

    def test_single_sub_period(self):
        """'LT B2' → single phase."""
        phases = self.parser.parse("LT B2")
        assert len(phases) == 1
        assert phases[0].sous_periode == "LT B2"
        assert phases[0].debut == -320
        assert phases[0].fin == -260

    def test_patriarche_eurfer(self):
        """'EURFER------' → age du Fer indéterminé."""
        phases = self.parser.parse("EURFER------")
        assert len(phases) == 1
        assert phases[0].debut == -800
        assert phases[0].fin == -25

    def test_boolean_columns_fer(self):
        """Boolean columns BdD Proto Alsace."""
        cols = {"BF3_HaC": 0, "HaD": 1, "LTAB": 0, "LTCD": 1}
        phases = self.parser.parse_boolean_columns(cols)
        subs = [p.sous_periode for p in phases]
        assert "Ha D1" in subs
        assert "LT C1" in subs

    def test_c14_calibrated(self):
        """'780-540 avant J.C' → Hallstatt range."""
        phases = self.parser.parse("780-540 avant J.C")
        assert len(phases) == 1
        assert phases[0].debut <= -540
        assert phases[0].fin >= -780

    def test_textual_age_du_fer(self):
        """'âge du Fer' → indéterminé with dates."""
        phases = self.parser.parse("Age du fer")
        assert len(phases) == 1
        assert phases[0].debut == -800
        assert phases[0].fin == -25

    def test_textual_bronze_fer(self):
        """'âge du Bronze-âge du Fer' → Hallstatt."""
        phases = self.parser.parse("Age du Bronze - age du Fer")
        assert len(phases) == 1
        assert phases[0].periode == "Hallstatt"

    def test_indetermine_fallback(self):
        """Unknown text → indéterminé."""
        phases = self.parser.parse("quelque chose")
        assert len(phases) == 1
        assert phases[0].periode == "indéterminé"

    def test_empty_string(self):
        phases = self.parser.parse("")
        assert len(phases) == 1
        assert phases[0].periode == "indéterminé"

    def test_arkeogis_pair(self):
        """Parse ArkeoGIS starting/ending pair."""
        phases = self.parser.parse_arkeogis_pair("-450:-380", "-380:-320")
        assert len(phases) >= 1
