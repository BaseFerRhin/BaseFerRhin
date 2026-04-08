"""Tests for DBF extractor."""

from pathlib import Path

import pytest

from src.infrastructure.extractors.dbf_extractor import DBFExtractor

_DATA = Path(__file__).resolve().parents[2] / "RawData" / "GrosFichiers - Béhague"
_EA_FR = _DATA / "ea_fr.dbf"
_AFEAF = _DATA / "2026_afeaf_lineaire.dbf"


@pytest.mark.skipif(not _EA_FR.exists(), reason="ea_fr.dbf not available")
class TestEaFrDBF:
    def setup_method(self):
        self.ext = DBFExtractor(
            column_mapping={
                "COMMUNE_PP": "commune",
                "VESTIGES": "type_mention",
                "X_DEGRE": "longitude_raw",
                "Y_DEGRE": "latitude_raw",
            }
        )
        self.records = self.ext.extract(_EA_FR)

    def test_row_count(self):
        assert len(self.records) == 42

    def test_coordinates_populated(self):
        with_coords = [r for r in self.records if r.latitude_raw is not None]
        assert len(with_coords) > 30

    def test_extra_fields(self):
        assert any(r.extra.get("EA_NATCODE") for r in self.records)


@pytest.mark.skipif(not _AFEAF.exists(), reason="afeaf_lineaire.dbf not available")
class TestAfeafDBF:
    def setup_method(self):
        self.ext = DBFExtractor()
        self.records = self.ext.extract(_AFEAF)

    def test_records_extracted(self):
        assert len(self.records) > 0

    def test_extraction_method(self):
        assert all(r.extraction_method == "dbf" for r in self.records)
