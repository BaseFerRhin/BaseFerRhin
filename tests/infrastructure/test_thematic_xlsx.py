"""Tests for thematic XLSX extractors."""

from pathlib import Path

import pytest

from src.infrastructure.extractors.thematic_xlsx_extractor import (
    BdDProtoAlsaceExtractor,
    HabitatsTombesRichesExtractor,
    InhumationsSilosExtractor,
    NecropoleExtractor,
)

_DATA = Path(__file__).resolve().parents[2] / "RawData" / "GrosFichiers - Béhague"


@pytest.mark.skipif(
    not (_DATA / "BdD_Proto_Alsace (1).xlsx").exists(),
    reason="BdD Proto Alsace not available",
)
class TestBdDProtoAlsace:
    def setup_method(self):
        self.ext = BdDProtoAlsaceExtractor()
        self.records = self.ext.extract(_DATA / "BdD_Proto_Alsace (1).xlsx")

    def test_excludes_bronze_only(self):
        assert len(self.records) < 800

    def test_all_have_iron_phases(self):
        for r in self.records:
            assert r.extra.get("phases_bool"), f"No Iron Age phases for {r.commune}"

    def test_extraction_method(self):
        assert all(r.extraction_method == "bdd_proto_alsace" for r in self.records)


@pytest.mark.skipif(
    not (_DATA / "20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx").exists(),
    reason="Nécropoles not available",
)
class TestNecropoles:
    def test_filter_alsace(self):
        ext = NecropoleExtractor(filter_departments=[67, 68])
        records = ext.extract(_DATA / "20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx")
        assert len(records) < 339
        assert len(records) > 100

    def test_no_filter(self):
        ext = NecropoleExtractor()
        records = ext.extract(_DATA / "20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx")
        assert len(records) >= 300

    def test_type_is_necropole(self):
        ext = NecropoleExtractor()
        records = ext.extract(_DATA / "20250324_necropoles_BFIIIb-HaD3_Als-Lor (1).xlsx")
        assert all(r.type_mention == "nécropole" for r in records)


@pytest.mark.skipif(
    not (_DATA / "20240419_Inhumations silos (1).xlsx").exists(),
    reason="Inhumations silos not available",
)
class TestInhumationsSilos:
    def setup_method(self):
        self.ext = InhumationsSilosExtractor()
        self.records = self.ext.extract(_DATA / "20240419_Inhumations silos (1).xlsx")

    def test_aggregation(self):
        assert len(self.records) < 86

    def test_individus_count(self):
        total = sum(r.extra.get("individus_count", 0) for r in self.records)
        assert total > 50

    def test_l93_coordinates(self):
        with_coords = [r for r in self.records if r.extra.get("x_l93")]
        assert len(with_coords) > 0


@pytest.mark.skipif(
    not (_DATA / "20240425_habitats-tombes riches_Als-Lor (1).xlsx").exists(),
    reason="Habitats-tombes riches not available",
)
class TestHabitatsTombesRiches:
    def setup_method(self):
        self.ext = HabitatsTombesRichesExtractor()
        self.records = self.ext.extract(
            _DATA / "20240425_habitats-tombes riches_Als-Lor (1).xlsx"
        )

    def test_records_extracted(self):
        assert len(self.records) > 0

    def test_pays_normalized(self):
        pays = {r.extra.get("pays") for r in self.records}
        assert "FR" in pays or "DE" in pays

    def test_parasitic_excluded(self):
        for r in self.records:
            assert "Manque" not in (r.extra.get("dept_land") or "")
