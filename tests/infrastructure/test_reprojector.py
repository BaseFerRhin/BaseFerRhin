"""Tests unitaires pour le Reprojector."""

import pytest

from src.infrastructure.geocoding.reprojector import Reprojector


class TestReprojector:
    def setup_method(self):
        self.reproj = Reprojector()

    def test_wgs84_to_l93_strasbourg(self):
        """Cathédrale de Strasbourg : WGS84 → L93 dans les bornes."""
        x_l93, y_l93, in_bounds = self.reproj.to_lambert93(7.7521, 48.5818, 4326)
        assert in_bounds
        assert 1_040_000 < x_l93 < 1_060_000
        assert 6_830_000 < y_l93 < 6_850_000

    def test_l93_passthrough(self):
        """Si déjà L93, aucune transformation."""
        x, y = 1_050_000.0, 6_840_000.0
        x_out, y_out, in_bounds = self.reproj.to_lambert93(x, y, 2154)
        assert x_out == x
        assert y_out == y
        assert in_bounds

    def test_out_of_bounds(self):
        """Coordonnées hors France métropolitaine."""
        _, _, in_bounds = self.reproj.to_lambert93(-74.0060, 40.7128, 4326)
        assert not in_bounds

    def test_transformer_cache(self):
        """Même Transformer réutilisé pour le même EPSG."""
        self.reproj.to_lambert93(7.0, 48.0, 4326)
        self.reproj.to_lambert93(8.0, 49.0, 4326)
        assert len(self.reproj._transformers) == 1

    def test_safe_none_inputs(self):
        x, y, ok = self.reproj.to_lambert93_safe(None, 48.0, 4326)
        assert x is None
        assert y is None
        assert not ok

    def test_safe_valid_inputs(self):
        x, y, ok = self.reproj.to_lambert93_safe(7.7521, 48.5818, 4326)
        assert ok
        assert x is not None
