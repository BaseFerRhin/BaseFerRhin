"""Tests for chronological and geographic filters."""

from src.domain.filters.chrono_filter import filter_records, is_age_du_fer
from src.domain.models.raw_record import RawRecord


class TestIsAgeDuFer:
    def test_hallstatt_mention(self):
        rec = RawRecord(periode_mention="Hallstatt D2")
        assert is_age_du_fer(rec)

    def test_la_tene_mention(self):
        rec = RawRecord(periode_mention="La Tène ancienne")
        assert is_age_du_fer(rec)

    def test_age_du_fer_text(self):
        rec = RawRecord(periode_mention="Age du fer")
        assert is_age_du_fer(rec)

    def test_dates_in_range(self):
        rec = RawRecord(extra={"datation_debut": -620, "datation_fin": -450})
        assert is_age_du_fer(rec)

    def test_dates_out_of_range(self):
        rec = RawRecord(periode_mention="néolithique", extra={"datation_debut": -5000, "datation_fin": -3000})
        assert not is_age_du_fer(rec)

    def test_boolean_phases(self):
        rec = RawRecord(extra={"phases_bool": ["HaD", "LTAB"]})
        assert is_age_du_fer(rec)

    def test_patriarche_method_trusted(self):
        rec = RawRecord(extraction_method="patriarche")
        assert is_age_du_fer(rec)

    def test_no_info_returns_false(self):
        rec = RawRecord(raw_text="something unknown")
        assert not is_age_du_fer(rec)

    def test_bronze_only_dates_excluded(self):
        rec = RawRecord(extra={"datation_debut": -1200, "datation_fin": -800})
        assert not is_age_du_fer(rec)

    def test_bronze_only_text_excluded(self):
        rec = RawRecord(periode_mention="âge du Bronze")
        assert not is_age_du_fer(rec)

    def test_bronze_fer_transition_included(self):
        rec = RawRecord(periode_mention="Age du bronze - Age du fer")
        assert is_age_du_fer(rec)

    def test_dates_spanning_transition(self):
        rec = RawRecord(extra={"datation_debut": -1200, "datation_fin": -450})
        assert is_age_du_fer(rec)


class TestFilterRecords:
    def test_chrono_filter(self):
        recs = [
            RawRecord(periode_mention="Hallstatt"),
            RawRecord(periode_mention="néolithique", extra={"datation_debut": -5000, "datation_fin": -3000}),
            RawRecord(periode_mention="La Tène B2"),
        ]
        result = filter_records(recs, chrono=True)
        assert len(result) == 2

    def test_no_filter(self):
        recs = [RawRecord(raw_text="x") for _ in range(5)]
        result = filter_records(recs, chrono=False)
        assert len(result) == 5

    def test_department_filter(self):
        recs = [
            RawRecord(extraction_method="patriarche", extra={"departement": "67"}),
            RawRecord(extraction_method="patriarche", extra={"departement": "57"}),
            RawRecord(extraction_method="patriarche", extra={"departement": "68"}),
        ]
        result = filter_records(recs, chrono=False, departments={67, 68})
        assert len(result) == 2
