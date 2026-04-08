"""Tests for ArkeoGIS extractor on real CSV files."""

from pathlib import Path

import pytest

from src.infrastructure.extractors.arkeogis_extractor import ArkeoGISExtractor

_DATA = Path(__file__).resolve().parents[2] / "RawData" / "GrosFichiers - Béhague"
_LOUP = _DATA / "20250806_LoupBernard_ArkeoGis.csv"
_ADAB = _DATA / "20250806_ADAB2011_ArkeoGis.csv"


@pytest.mark.skipif(not _LOUP.exists(), reason="LoupBernard CSV not available")
class TestLoupBernard:
    def setup_method(self):
        self.ext = ArkeoGISExtractor()
        self.records = self.ext.extract(_LOUP)

    def test_row_count(self):
        assert len(self.records) >= 100

    def test_source_path(self):
        assert all(r.source_path.endswith(".csv") for r in self.records)

    def test_extraction_method(self):
        assert all(r.extraction_method == "arkeogis" for r in self.records)

    def test_akg_id_populated(self):
        assert all(r.extra.get("SITE_AKG_ID") for r in self.records)

    def test_all_centroid(self):
        assert all(r.extra.get("precision_localisation") == "centroïde" for r in self.records)

    def test_coordinates_present(self):
        assert all(r.latitude_raw is not None and r.longitude_raw is not None for r in self.records)

    def test_datation_parsed(self):
        for r in self.records:
            if r.extra.get("datation_debut") is not None:
                assert isinstance(r.extra["datation_debut"], int)


@pytest.mark.skipif(not _ADAB.exists(), reason="ADAB CSV not available")
class TestADAB:
    def setup_method(self):
        self.ext_all = ArkeoGISExtractor()
        self.ext_filtered = ArkeoGISExtractor(filter_age_du_fer=True)

    def test_full_extraction(self):
        records = self.ext_all.extract(_ADAB)
        assert len(records) >= 600

    def test_filtered_less(self):
        all_recs = self.ext_all.extract(_ADAB)
        filtered = self.ext_filtered.extract(_ADAB)
        assert len(filtered) < len(all_recs)

    def test_comment_parsing(self):
        records = self.ext_all.extract(_ADAB)
        with_typ = [r for r in records if r.extra.get("TYP_FEIN")]
        assert len(with_typ) > 0

    def test_type_mapping(self):
        records = self.ext_all.extract(_ADAB)
        types = {r.type_mention for r in records}
        assert "nécropole" in types or "habitat" in types


class TestTypeMapping:
    def test_enceinte_is_oppidum(self):
        assert ArkeoGISExtractor._map_type("Enceinte") == "oppidum"

    def test_funeraire_is_necropole(self):
        assert ArkeoGISExtractor._map_type("Funéraire") == "nécropole"

    def test_ceramique_is_indetermine(self):
        assert ArkeoGISExtractor._map_type("Céramique") == "indéterminé"

    def test_habitat_mapping(self):
        assert ArkeoGISExtractor._map_type("Habitat") == "habitat"


class TestPrecision:
    def test_centroid(self):
        assert ArkeoGISExtractor._resolve_precision("Oui", "") == "centroïde"

    def test_exact_20m(self):
        assert ArkeoGISExtractor._resolve_precision("Non", "GENAUIGK_T : mit 20 m Toleranz") == "exact"

    def test_approx(self):
        assert ArkeoGISExtractor._resolve_precision("Non", "GENAUIGK_T : mit Ungenauigkeit bis zu 200m") == "approx"
