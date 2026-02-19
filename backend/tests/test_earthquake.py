"""Tests for earthquake service and parser."""

import pytest
from datetime import datetime

from app.parsers.earthquake_parser import (
    parse_datetime,
    parse_coordinates,
    parse_earthquake,
    parse_earthquake_list,
)
from app.models.earthquake import Earthquake
from app.services.earthquake_service import haversine_distance


class TestEarthquakeParser:
    """Test earthquake parser functions."""
    
    def test_parse_datetime_wib(self):
        """Test parsing datetime with WIB timezone."""
        dt = parse_datetime("16 Feb 2026", "13:15:30 WIB")
        # WIB is UTC+7, so 13:15:30 WIB = 06:15:30 UTC
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 16
        assert dt.hour == 6
        assert dt.minute == 15
        assert dt.second == 30
    
    def test_parse_datetime_wita(self):
        """Test parsing datetime with WITA timezone."""
        dt = parse_datetime("16 Feb 2026", "13:15:30 WITA")
        # WITA is UTC+8, so 13:15:30 WITA = 05:15:30 UTC
        assert dt.hour == 5
    
    def test_parse_coordinates_ls_bt(self):
        """Test parsing LS (South) and BT (East) coordinates."""
        lat, lon, lat_text, lon_text = parse_coordinates("6.89 LS", "109.67 BT")
        assert lat == -6.89  # South is negative
        assert lon == 109.67  # East is positive
        assert lat_text == "6.89 LS"
        assert lon_text == "109.67 BT"
    
    def test_parse_coordinates_lu_bb(self):
        """Test parsing LU (North) and BB (West) coordinates."""
        lat, lon, lat_text, lon_text = parse_coordinates("6.89 LU", "109.67 BB")
        assert lat == 6.89  # North is positive
        assert lon == -109.67  # West is negative
    
    def test_parse_earthquake(self, sample_autogempa):
        """Test parsing single earthquake."""
        gempa_data = sample_autogempa["Infogempa"]["gempa"]
        eq = parse_earthquake(gempa_data)
        
        assert isinstance(eq, Earthquake)
        assert eq.magnitude == 5.4
        assert eq.depth_km == 10.0
        assert eq.lat == -6.89
        assert eq.lon == 109.67
        assert eq.region == "18 km TimurLaut Pekalongan"
        assert eq.tsunami_potential == "Tidak berpotensi tsunami"
        assert eq.felt_report == "III Pekalongan, II Batang"
        assert eq.shakemap_url == "https://data.bmkg.go.id/DataMKG/TEWS/20260216131530.mmi.jpg"
    
    def test_parse_earthquake_list(self, sample_gempaterkini):
        """Test parsing list of earthquakes."""
        earthquakes = parse_earthquake_list(sample_gempaterkini)
        
        assert len(earthquakes) == 2
        assert earthquakes[0].magnitude == 5.4
        assert earthquakes[1].magnitude == 5.1


class TestHaversineDistance:
    """Test haversine distance calculation."""
    
    def test_same_point(self):
        """Distance from point to itself should be 0."""
        dist = haversine_distance(-6.89, 109.67, -6.89, 109.67)
        assert dist == 0
    
    def test_known_distance(self):
        """Test approximate distance between two known points."""
        # Jakarta to Bandung (approximately 120 km)
        dist = haversine_distance(-6.2, 106.85, -6.9, 107.6)
        # Should be roughly 110-130 km
        assert 100 < dist < 150


class TestEarthquakeModel:
    """Test Earthquake model."""
    
    def test_model_dump(self):
        """Test model serialization with alias."""
        eq = Earthquake(
            occurred_at=datetime(2026, 2, 16, 6, 15, 30),
            magnitude=5.4,
            depth_km=10.0,
            lat=-6.89,
            lon=109.67,
            lat_text="6.89 LS",
            lon_text="109.67 BT",
            region="Test Region",
            tsunami_potential=None,
            felt_report=None,
            shakemap_url=None,
        )
        
        # Test with alias (for API response)
        data = eq.model_dump(by_alias=True)
        assert "datetime" in data
        assert data["magnitude"] == 5.4
        assert data["lat"] == -6.89
        assert data["region"] == "Test Region"
        
        # Test without alias (internal use)
        data_internal = eq.model_dump()
        assert "occurred_at" in data_internal
        assert "datetime" not in data_internal
