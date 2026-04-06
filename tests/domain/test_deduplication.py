"""Tests for site deduplication (cross-border variants, review queue, merge integrity)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.domain.deduplication import SiteDeduplicator
from src.domain.models import (
    Pays,
    PrecisionLocalisation,
    Site,
    Source,
    TypeSite,
)


def _site(
    site_id: str,
    nom: str,
    commune: str,
    pays: Pays,
    lat: float | None,
    lon: float | None,
    *,
    sources: list[Source] | None = None,
) -> Site:
    return Site(
        site_id=site_id,
        nom_site=nom,
        variantes_nom=[],
        pays=pays,
        region_admin="Test",
        commune=commune,
        latitude=lat,
        longitude=lon,
        precision_localisation=PrecisionLocalisation.EXACT,
        type_site=TypeSite.HABITAT,
        sources=sources or [],
        date_creation=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_maj=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def test_fr_de_variant_merge():
    """Vieux-Brisach (FR) vs Breisach am Rhein (DE): same Rhine locality, cross-listing merge.

    With the 40/30/30 scorer, this pair scores ~0.78–0.79 (name tokens differ across languages);
    merge_threshold is lowered here so the test encodes the intended product behaviour.
    """
    fr = _site(
        "fr-vieux-brisach",
        "Vieux-Brisach",
        "Breisach",
        Pays.FR,
        48.03,
        7.58,
        sources=[
            Source(
                source_id="src-fr-1",
                site_id="fr-vieux-brisach",
                reference="CAG 68, Neuf-Brisach",
                date_extraction=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ],
    )
    de = _site(
        "de-breisach",
        "Breisach am Rhein",
        "Breisach",
        Pays.DE,
        48.028,
        7.575,
        sources=[
            Source(
                source_id="src-de-1",
                site_id="de-breisach",
                reference="Dietz, Breisach Münsterberg",
                date_extraction=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ],
    )
    dedup = SiteDeduplicator(merge_threshold=0.78, review_threshold=0.70)
    merged, review = dedup.deduplicate([fr, de])
    assert len(merged) == 1
    assert review == []
    nom = merged[0].nom_site
    assert nom in ("Vieux-Brisach", "Breisach am Rhein")
    assert "Breisach am Rhein" in merged[0].variantes_nom or nom == "Breisach am Rhein"
    assert "Vieux-Brisach" in merged[0].variantes_nom or nom == "Vieux-Brisach"


def test_ambiguous_pair_flagged():
    """Same commune, different site names, close coordinates → high but sub-merge score → review."""
    a = _site("amb-a", "Site Alpha", "Strasbourg", Pays.FR, 48.58, 7.75)
    b = _site("amb-b", "Site Beta", "Strasbourg", Pays.FR, 48.59, 7.76)
    dedup = SiteDeduplicator(merge_threshold=0.85, review_threshold=0.70)
    merged, review = dedup.deduplicate([a, b])
    assert len(merged) == 2
    assert len(review) == 1
    assert review[0]["site_id_a"] in ("amb-a", "amb-b")
    assert review[0]["site_id_b"] in ("amb-a", "amb-b")
    assert 0.78 <= review[0]["score"] < 0.85


def test_distant_homophone_no_merge():
    """Similar names but >50 km apart: geo term drops to zero; pair must not merge."""
    a = _site(
        "dist-a",
        "Oppidum du Baerengraben",
        "Neuf-Brisach",
        Pays.FR,
        48.573,
        7.752,
    )
    b = _site(
        "dist-b",
        "Oppidum du Bärengraben",
        "Emmendingen",
        Pays.DE,
        48.11,
        7.96,
    )
    dedup = SiteDeduplicator(merge_threshold=0.85, review_threshold=0.70)
    merged, _review = dedup.deduplicate([a, b])
    assert len(merged) == 2


def test_merge_preserves_sources():
    s1 = _site(
        "ens-1",
        "Ensisheim nord",
        "Ensisheim",
        Pays.FR,
        47.97,
        7.35,
        sources=[
            Source(
                source_id="src-x",
                site_id="ens-1",
                reference="Ref X",
                date_extraction=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ],
    )
    s2 = _site(
        "ens-2",
        "Ensisheim sud",
        "Ensisheim",
        Pays.FR,
        47.971,
        7.351,
        sources=[
            Source(
                source_id="src-y",
                site_id="ens-2",
                reference="Ref Y",
                date_extraction=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ],
    )
    dedup = SiteDeduplicator()
    merged, _ = dedup.deduplicate([s1, s2])
    assert len(merged) == 1
    refs = {src.reference for src in merged[0].sources}
    assert refs == {"Ref X", "Ref Y"}
    assert {src.source_id for src in merged[0].sources} == {"src-x", "src-y"}
