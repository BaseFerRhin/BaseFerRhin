"""Tests for Patriarche extractor with EA_IDENT parsing."""

from pathlib import Path

import pytest

from src.infrastructure.extractors.patriarche_extractor import PatriarcheExtractor

_DATA = Path(__file__).resolve().parents[2] / "RawData" / "GrosFichiers - Béhague"
_PATRIARCHE = _DATA / "20250806_Patriarche_ageFer.xlsx"
_EA_FR = _DATA / "ea_fr.dbf"


class TestEAIdentParsing:
    def setup_method(self):
        self.ext = PatriarcheExtractor()

    def test_six_slash_standard(self):
        parts = "8342 / 67 019 0009 / BALDENHEIM /  / SCHLITTWEG / habitat / Age du fer - Gallo-romain".split(" / ")
        commune, lieu_dit, type_m, periode = self.ext._parse_parts(parts)
        assert commune == "BALDENHEIM"
        assert lieu_dit == "SCHLITTWEG"
        assert type_m == "habitat"
        assert "fer" in periode.lower() or "Fer" in periode

    def test_reversed_order(self):
        parts = "10901 / 67 008 0013 / ALTORF /  / Birckenwald / tumulus / Age du bronze - Age du fer".split(" / ")
        commune, lieu_dit, type_m, periode = self.ext._parse_parts(parts)
        assert commune == "ALTORF"
        assert type_m == "tumulus"
        assert "bronze" in periode.lower() or "fer" in periode.lower()

    def test_five_slash_missing_field(self):
        parts = "12163 / 67 008 0022 / ALTORF /  / Osterlaeng / Age du fer".split(" / ")
        commune, lieu_dit, type_m, periode = self.ext._parse_parts(parts)
        assert commune == "ALTORF"
        assert periode is not None and "fer" in periode.lower()

    def test_seven_slash(self):
        parts = "1121 / 67 001 0006 / ACHENHEIM /  / Breite / Age du bronze - Age du fer / fosse".split(" / ")
        commune, lieu_dit, type_m, periode = self.ext._parse_parts(parts)
        assert commune == "ACHENHEIM"
        assert lieu_dit == "Breite"


@pytest.mark.skipif(not _PATRIARCHE.exists(), reason="Patriarche XLSX not available")
class TestPatriarcheExtraction:
    def setup_method(self):
        dbf = _EA_FR if _EA_FR.exists() else None
        self.ext = PatriarcheExtractor(dbf_path=dbf)
        self.records = self.ext.extract(_PATRIARCHE)

    def test_row_count(self):
        assert len(self.records) >= 800

    def test_extraction_method(self):
        assert all(r.extraction_method == "patriarche" for r in self.records)

    def test_ea_populated(self):
        with_ea = [r for r in self.records if r.extra.get("patriarche_ea")]
        assert len(with_ea) > 0

    def test_communes_extracted(self):
        with_commune = [r for r in self.records if r.commune]
        assert len(with_commune) > len(self.records) * 0.9

    def test_coordinates_from_dbf(self):
        if not _EA_FR.exists():
            pytest.skip("ea_fr.dbf not available")
        with_coords = [r for r in self.records if r.latitude_raw is not None]
        assert len(with_coords) > 0
