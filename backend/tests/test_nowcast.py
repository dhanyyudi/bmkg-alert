"""Tests for nowcast service and parsers."""

import pytest
from datetime import datetime, timezone

from app.parsers.rss_parser import parse_rss_feed, parse_rss_date, extract_alert_code_from_link
from app.parsers.cap_parser import parse_cap_xml, parse_cap_datetime, parse_polygon
from app.models.nowcast import ActiveProvince, Warning, Area


class TestRssParser:
    """Test RSS parser functions."""
    
    def test_parse_rss_date_with_timezone(self):
        """Test parsing RSS date with timezone offset."""
        dt = parse_rss_date("Mon, 16 Feb 2026 22:50:00 +0700")
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 16
        assert dt.hour == 22
        assert dt.minute == 50
        assert dt.second == 00
        assert dt.utcoffset().seconds == 7 * 3600  # +07:00
    
    def test_parse_rss_date_utc(self):
        """Test parsing RSS date with UTC timezone."""
        dt = parse_rss_date("Mon, 16 Feb 2026 16:17:19 +0000")
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 16
        assert dt.utcoffset().seconds == 0
    
    def test_extract_alert_code_from_link(self):
        """Test extracting alert code from RSS link."""
        link = "https://www.bmkg.go.id/alerts/nowcast/id/CBT20260216004_alert.xml"
        code = extract_alert_code_from_link(link)
        assert code == "CBT20260216004"
    
    def test_parse_rss_feed(self, load_fixture):
        """Test parsing RSS feed XML."""
        xml_content = load_fixture("rss_active.xml")
        provinces = parse_rss_feed(xml_content, "id")
        
        assert len(provinces) == 3
        
        # Check first province (Banten)
        assert provinces[0].code == "CBT20260216004"
        assert provinces[0].province == "Banten"
        assert "Bojonegara" in provinces[0].description
        assert provinces[0].detail_url == "/v1/nowcast/CBT20260216004"
        
        # Check second province (Jawa Tengah)
        assert provinces[1].code == "CJG20260216005"
        assert provinces[1].province == "Jawa Tengah"
        assert "Wiradesa" in provinces[1].description


class TestCapParser:
    """Test CAP parser functions."""
    
    def test_parse_cap_datetime(self):
        """Test parsing CAP datetime format."""
        dt = parse_cap_datetime("2026-02-16T22:50:00+07:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 16
        assert dt.hour == 22
        assert dt.minute == 50
    
    def test_parse_cap_datetime_none(self):
        """Test parsing None datetime."""
        dt = parse_cap_datetime(None)
        assert dt is None
    
    def test_parse_cap_datetime_empty(self):
        """Test parsing empty datetime."""
        dt = parse_cap_datetime("")
        assert dt is None
    
    def test_parse_polygon(self):
        """Test parsing polygon coordinates."""
        polygon_str = "-5.981,105.994 -6.004,106.022 -6.010,106.029"
        points = parse_polygon(polygon_str)
        
        assert len(points) == 3
        assert points[0] == [-5.981, 105.994]
        assert points[1] == [-6.004, 106.022]
        assert points[2] == [-6.010, 106.029]
    
    def test_parse_polygon_empty(self):
        """Test parsing empty polygon."""
        points = parse_polygon("")
        assert points == []
    
    def test_parse_cap_xml_banten(self, load_fixture):
        """Test parsing CAP XML for Banten."""
        xml_content = load_fixture("cap_banten.xml")
        warning = parse_cap_xml(xml_content)
        
        assert warning is not None
        assert warning.identifier == "2.49.0.1.360.0.2026.02.16.16.36.004"
        assert warning.event == "Hujan Lebat dan Petir"
        assert warning.severity == "Moderate"
        assert warning.urgency == "Immediate"
        assert warning.certainty == "Observed"
        assert warning.headline == "Hujan Lebat disertai Petir di Banten"
        assert "Bojonegara" in warning.description
        assert warning.sender == "Badan Meteorologi Klimatologi dan Geofisika"
        assert warning.infographic_url == "https://nowcasting.bmkg.go.id/infografis/CBT/2026/02/16/infografis.jpg"
        assert len(warning.areas) == 1
        assert warning.areas[0].name == "Banten"
        assert warning.areas[0].polygon is not None
        assert len(warning.areas[0].polygon) > 0
    
    def test_parse_cap_xml_jateng(self, load_fixture):
        """Test parsing CAP XML for Jawa Tengah."""
        xml_content = load_fixture("cap_jateng.xml")
        warning = parse_cap_xml(xml_content)
        
        assert warning is not None
        assert warning.identifier == "2.49.0.1.360.0.2026.02.16.16.45.005"
        assert warning.event == "Hujan Lebat dan Petir"
        assert warning.severity == "Moderate"
        assert warning.urgency == "Expected"
        assert warning.certainty == "Likely"
        assert "Wiradesa" in warning.description
        assert warning.areas[0].name == "Jawa Tengah"


class TestNowcastModels:
    """Test Nowcast Pydantic models."""
    
    def test_active_province_model(self):
        """Test ActiveProvince model creation."""
        province = ActiveProvince(
            code="CBT20260216004",
            province="Banten",
            description="Test description",
            published_at=datetime.now(timezone.utc),
            detail_url="/v1/nowcast/CBT20260216004",
        )
        
        assert province.code == "CBT20260216004"
        assert province.province == "Banten"
        assert province.detail_url == "/v1/nowcast/CBT20260216004"
    
    def test_warning_model(self):
        """Test Warning model creation."""
        warning = Warning(
            identifier="TEST-001",
            event="Hujan Lebat",
            severity="Moderate",
            urgency="Expected",
            certainty="Likely",
            headline="Test Headline",
            description="Test Description",
            sender="BMKG",
            is_expired=False,
            effective=datetime.now(timezone.utc),
            expires=datetime.now(timezone.utc),
            areas=[
                Area(name="Test Area", polygon=[[-6.0, 106.0], [-6.1, 106.1]])
            ],
        )
        
        assert warning.identifier == "TEST-001"
        assert warning.event == "Hujan Lebat"
        assert len(warning.areas) == 1
        assert warning.areas[0].name == "Test Area"
    
    def test_area_model(self):
        """Test Area model creation."""
        area = Area(
            name="Kec. Wiradesa, Kab. Pekalongan",
            polygon=[[-6.89, 109.67], [-6.88, 109.68]]
        )
        
        assert area.name == "Kec. Wiradesa, Kab. Pekalongan"
        assert area.polygon == [[-6.89, 109.67], [-6.88, 109.68]]
    
    def test_area_model_without_polygon(self):
        """Test Area model without polygon."""
        area = Area(name="Test Area")
        
        assert area.name == "Test Area"
        assert area.polygon is None


class TestModelSerialization:
    """Test model serialization."""
    
    def test_province_serialization(self):
        """Test ActiveProvince JSON serialization."""
        province = ActiveProvince(
            code="CBT20260216004",
            province="Banten",
            description="Test description",
            published_at=datetime(2026, 2, 16, 15, 50, 0, tzinfo=timezone.utc),
            detail_url="/v1/nowcast/CBT20260216004",
        )
        
        data = province.model_dump(mode='json')
        assert data["code"] == "CBT20260216004"
        assert data["province"] == "Banten"
        assert "published_at" in data
    
    def test_warning_serialization(self):
        """Test Warning JSON serialization."""
        warning = Warning(
            identifier="TEST-001",
            event="Hujan Lebat",
            severity="Moderate",
            urgency="Expected",
            certainty="Likely",
            headline="Test Headline",
            description="Test Description",
            sender="BMKG",
            is_expired=False,
            effective=datetime.now(timezone.utc),
            expires=datetime.now(timezone.utc),
        )
        
        data = warning.model_dump(mode='json')
        assert data["identifier"] == "TEST-001"
        assert data["severity"] == "Moderate"
        assert data["is_expired"] is False
