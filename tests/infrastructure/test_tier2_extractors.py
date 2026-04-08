"""Tests for Tier 2 extractors: AFEAF, ODS, CAG."""

from pathlib import Path

import pytest

from src.infrastructure.extractors.afeaf_extractor import AFEAFExtractor
from src.infrastructure.extractors.ods_extractor import ODSExtractor
from src.infrastructure.extractors.doc_extractor import DocExtractor
from src.infrastructure.extractors.cag_notice_extractor import CAGNoticeExtractor

_DATA = Path(__file__).resolve().parents[2] / "RawData" / "GrosFichiers - Béhague"


class TestAFEAFHeaderReconstruction:
    def test_reconstruct(self):
        row0 = ("info SITE", None, None, "REMARQUES")
        row1 = ("DPT", "SITE", "N° ST", "REMARQUES")
        cols = AFEAFExtractor._reconstruct_headers(row0, row1)
        assert cols[0] == "info SITE.DPT"
        assert cols[1] == "info SITE.SITE"
        assert cols[2] == "info SITE.N° ST"
        assert cols[3] == "REMARQUES GENERALES.REMARQUES" or "REMARQUES" in cols[3]


@pytest.mark.skipif(
    not (_DATA / "BDD-fun_AFEAF24-total_04.12 (1).xlsx").exists(),
    reason="AFEAF file not available",
)
class TestAFEAFExtraction:
    def setup_method(self):
        self.ext = AFEAFExtractor()
        self.records = self.ext.extract(_DATA / "BDD-fun_AFEAF24-total_04.12 (1).xlsx")

    def test_records_extracted(self):
        assert len(self.records) > 10

    def test_extraction_method(self):
        assert all(r.extraction_method == "afeaf" for r in self.records)

    def test_type_is_necropole(self):
        assert all(r.type_mention == "nécropole" for r in self.records)

    def test_departement_populated(self):
        with_dept = [r for r in self.records if r.extra.get("departement")]
        assert len(with_dept) > 0

    def test_funeraire_data(self):
        with_fun = [r for r in self.records if r.extra.get("funeraire")]
        assert len(with_fun) > 0


@pytest.mark.skipif(
    not (_DATA / "20240425_mobilier_sepult_def (1).ods").exists(),
    reason="ODS file not available",
)
class TestODSExtraction:
    def setup_method(self):
        self.ext = ODSExtractor()
        self.records = self.ext.extract(_DATA / "20240425_mobilier_sepult_def (1).ods")

    def test_records_extracted(self):
        assert len(self.records) > 100

    def test_extraction_method(self):
        assert all(r.extraction_method == "ods" for r in self.records)

    def test_communes_present(self):
        with_commune = [r for r in self.records if r.commune]
        assert len(with_commune) > 50


class TestCAGNoticeParser:
    def setup_method(self):
        self.parser = CAGNoticeExtractor(source_label="cag_68")

    def test_parse_notices(self):
        text = """001 - ALGOLSHEIM

La localité se situe à proximité du Rhin.

(004 AH) - Au lieu-dit Rheingraben, des tumulus ont été fouillés
en 1892. Datation : Hallstatt. Tessons de céramique.

002 - ALTENACH

Village sans vestiges protohistoriques connus.

003 - ALTKIRCH

Fortification de hauteur, oppidum. Âge du fer.
"""
        records = self.parser.extract_from_text(text, "test.doc")
        assert len(records) >= 2
        communes = [r.commune for r in records]
        assert "ALGOLSHEIM" in communes
        assert "ALTKIRCH" in communes

    def test_type_guessing(self):
        assert CAGNoticeExtractor._guess_type(["tumulus", "céramique"]) == "nécropole"
        assert CAGNoticeExtractor._guess_type(["oppidum"]) == "oppidum"
        assert CAGNoticeExtractor._guess_type(["silo", "fosse"]) == "habitat"


@pytest.mark.skipif(
    not (_DATA / "cag_68_texte.doc").exists(),
    reason="CAG 68 texte.doc not available",
)
class TestCAG68DOCExtraction:
    def test_extract_text(self):
        ext = DocExtractor()
        text = ext.extract_text(_DATA / "cag_68_texte.doc")
        assert len(text) > 10000
        assert "Algols" in text or "ALGOLSHEIM" in text or "001" in text

    def test_parse_notices(self):
        ext = DocExtractor()
        text = ext.extract_text(_DATA / "cag_68_texte.doc")
        parser = CAGNoticeExtractor(source_label="cag_68")
        records = parser.extract_from_text(text, str(_DATA / "cag_68_texte.doc"))
        assert len(records) > 30
