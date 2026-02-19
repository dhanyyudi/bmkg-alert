"""Tests for wilayah service and routes."""

import pytest
from fastapi.testclient import TestClient

from app.models.wilayah import WilayahLevel
from app.services.wilayah_service import WilayahService


class TestWilayahService:
    """Test wilayah service functionality."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh wilayah service instance."""
        svc = WilayahService()
        svc.load_data()
        return svc
    
    def test_load_data(self, service):
        """Test that data loads correctly."""
        stats = service.get_stats()
        
        # Should have 34 provinces
        assert stats["provinces"] == 34
        
        # Should have many districts, subdistricts, and villages
        assert stats["districts"] > 400  # ~514 kabupaten/kota
        assert stats["subdistricts"] > 6000  # ~7000 kecamatan
        assert stats["villages"] > 70000  # ~84000 desa/kelurahan
        assert stats["total"] > 75000
    
    def test_get_provinces(self, service):
        """Test getting all provinces."""
        provinces = service.get_provinces()
        
        assert len(provinces) == 34
        
        # Check some known provinces
        codes = [p.code for p in provinces]
        assert "11" in codes  # ACEH
        assert "31" in codes  # DKI JAKARTA
        assert "33" in codes  # JAWA TENGAH
        assert "34" in codes  # D.I. YOGYAKARTA
    
    def test_get_districts(self, service):
        """Test getting districts for a province."""
        districts = service.get_districts("33")
        
        # Jawa Tengah should have 35 districts (29 kab + 6 kota)
        assert len(districts) == 35
        
        # Check some known districts
        codes = [d.code for d in districts]
        assert "33.26" in codes  # Kab. Pekalongan
        assert "33.74" in codes  # Kota Semarang
        
        # Check level is district
        for d in districts:
            assert d.level == WilayahLevel.DISTRICT
    
    def test_get_subdistricts(self, service):
        """Test getting subdistricts for a district."""
        subdistricts = service.get_subdistricts("33.26")
        
        # Kab. Pekalongan has 19 kecamatan
        assert len(subdistricts) == 19
        
        # Check Wiradesa is there
        names = [s.name for s in subdistricts]
        assert "Wiradesa" in names
        
        # Check level is subdistrict
        for s in subdistricts:
            assert s.level == WilayahLevel.SUBDISTRICT
    
    def test_get_villages(self, service):
        """Test getting villages for a subdistrict."""
        villages = service.get_villages("33.26.16")
        
        # Wiradesa has multiple villages
        assert len(villages) > 0
        
        # Check level is village
        for v in villages:
            assert v.level == WilayahLevel.VILLAGE
    
    def test_search(self, service):
        """Test searching wilayah."""
        results = service.search("wiradesa")
        
        # Should find Wiradesa
        assert len(results) >= 1
        
        # Check result structure
        wiradesa = next(r for r in results if r.name == "Wiradesa")
        assert wiradesa.code == "33.26.16"
        assert wiradesa.level == WilayahLevel.SUBDISTRICT
        assert "Jawa Tengah" in wiradesa.full_path
        assert "Pekalongan" in wiradesa.full_path
        assert wiradesa.parent_code == "33.26"
    
    def test_search_case_insensitive(self, service):
        """Test that search is case-insensitive."""
        results_lower = service.search("jakarta")
        results_upper = service.search("JAKARTA")
        results_mixed = service.search("JaKaRtA")
        
        assert len(results_lower) == len(results_upper) == len(results_mixed)
    
    def test_search_limit(self, service):
        """Test search result limit."""
        # Search for something common that would have many results
        results = service.search("a", limit=10)
        assert len(results) == 10
    
    def test_get_by_code(self, service):
        """Test getting wilayah by code."""
        # Province
        jateng = service.get_by_code("33")
        assert jateng is not None
        assert jateng.name == "JAWA TENGAH"
        assert jateng.level == WilayahLevel.PROVINCE
        
        # District
        pekalongan = service.get_by_code("33.26")
        assert pekalongan is not None
        assert "PEKALONGAN" in pekalongan.name
        assert pekalongan.level == WilayahLevel.DISTRICT
        
        # Non-existent
        not_found = service.get_by_code("99.99")
        assert not_found is None
    
    def test_determine_level(self, service):
        """Test level determination from code."""
        assert service._determine_level("11") == WilayahLevel.PROVINCE
        assert service._determine_level("11.01") == WilayahLevel.DISTRICT
        assert service._determine_level("11.01.01") == WilayahLevel.SUBDISTRICT
        assert service._determine_level("11.01.01.2001") == WilayahLevel.VILLAGE


class TestWilayahAPI:
    """Test wilayah API endpoints."""
    
    def test_get_provinces(self, client):
        """Test GET /v1/wilayah/provinces."""
        response = client.get("/v1/wilayah/provinces")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert "attribution" in data
        
        assert len(data["data"]) == 34
        assert data["meta"]["count"] == 34
        
        # Check first province structure
        province = data["data"][0]
        assert "code" in province
        assert "name" in province
    
    def test_get_districts(self, client):
        """Test GET /v1/wilayah/districts."""
        response = client.get("/v1/wilayah/districts?province=33")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) == 35  # Jawa Tengah has 35 districts
        assert data["meta"]["count"] == 35
        assert data["meta"]["province_code"] == "33"
        assert "province_name" in data["meta"]
    
    def test_get_districts_invalid_province(self, client):
        """Test GET /v1/wilayah/districts with invalid province."""
        response = client.get("/v1/wilayah/districts?province=99")
        
        assert response.status_code == 404
        
        data = response.json()
        assert data["error"] == "not_found"
    
    def test_get_districts_missing_province(self, client):
        """Test GET /v1/wilayah/districts without province parameter."""
        response = client.get("/v1/wilayah/districts")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_subdistricts(self, client):
        """Test GET /v1/wilayah/subdistricts."""
        response = client.get("/v1/wilayah/subdistricts?district=33.26")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) == 19  # Kab. Pekalongan has 19 subdistricts
        assert data["meta"]["district_code"] == "33.26"
    
    def test_get_subdistricts_invalid_district(self, client):
        """Test GET /v1/wilayah/subdistricts with invalid district."""
        response = client.get("/v1/wilayah/subdistricts?district=99.99")
        
        assert response.status_code == 404
    
    def test_get_villages(self, client):
        """Test GET /v1/wilayah/villages."""
        response = client.get("/v1/wilayah/villages?subdistrict=33.26.16")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) > 0
        assert data["meta"]["subdistrict_code"] == "33.26.16"
    
    def test_search(self, client):
        """Test GET /v1/wilayah/search."""
        response = client.get("/v1/wilayah/search?q=wiradesa")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "meta" in data
        
        # Should find Wiradesa
        wiradesa = next((r for r in data["data"] if r["name"] == "Wiradesa"), None)
        assert wiradesa is not None
        assert wiradesa["code"] == "33.26.16"
        assert wiradesa["level"] == "subdistrict"
        assert "full_path" in wiradesa
        assert wiradesa["parent_code"] == "33.26"
    
    def test_search_case_insensitive(self, client):
        """Test search is case-insensitive."""
        response_lower = client.get("/v1/wilayah/search?q=jakarta")
        response_upper = client.get("/v1/wilayah/search?q=JAKARTA")
        
        assert len(response_lower.json()["data"]) == len(response_upper.json()["data"])
    
    def test_search_too_short(self, client):
        """Test search with query too short."""
        response = client.get("/v1/wilayah/search?q=x")
        
        assert response.status_code == 422  # Validation error (min_length=2)
    
    def test_search_with_limit(self, client):
        """Test search with custom limit."""
        response = client.get("/v1/wilayah/search?q=kec&limit=5")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) == 5
        assert data["meta"]["limit"] == 5
