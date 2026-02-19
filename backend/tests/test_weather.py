"""Tests for weather forecast service and parser."""

import pytest
from datetime import datetime, timezone

from app.parsers.weather_parser import (
    get_icon_url,
    get_visibility_text,
    parse_location,
    parse_forecast_entry,
    group_forecast_by_date,
    parse_weather_forecast,
    find_current_forecast,
    WEATHER_CODE_NAMES,
)
from app.models.weather import Location, ForecastEntry, ForecastDay, WeatherForecast


class TestWeatherCodeMapping:
    """Test weather code mappings."""
    
    def test_all_codes_have_names(self):
        """All weather codes should have name mappings."""
        from app.models.enums import WeatherCode
        
        for code in WeatherCode:
            assert code.value in WEATHER_CODE_NAMES
            names = WEATHER_CODE_NAMES[code.value]
            assert len(names) == 2
            assert names[0]  # Indonesian name
            assert names[1]  # English name
    
    def test_weather_code_cerah(self):
        """Test clear weather code."""
        names = WEATHER_CODE_NAMES[0]
        assert names[0] == "Cerah"
        assert names[1] == "Clear"
    
    def test_weather_code_hujan_lebat(self):
        """Test heavy rain weather code."""
        names = WEATHER_CODE_NAMES[45]
        assert names[0] == "Hujan Lebat"
        assert names[1] == "Heavy Rain"


class TestGetIconUrl:
    """Test icon URL generation."""
    
    def test_clear_day_icon(self):
        """Clear weather daytime icon."""
        url = get_icon_url(0, is_day=True)
        assert "cerah-am.svg" in url
    
    def test_clear_night_icon(self):
        """Clear weather nighttime icon."""
        url = get_icon_url(0, is_day=False)
        assert "cerah-pm.svg" in url
    
    def test_rain_icon(self):
        """Rain weather icon."""
        url = get_icon_url(10, is_day=True)
        assert "hujan-sedang-am.svg" in url
    
    def test_thunderstorm_icon(self):
        """Thunderstorm weather icon."""
        url = get_icon_url(95, is_day=True)
        assert "petir-am.svg" in url
    
    def test_unknown_code_fallback(self):
        """Unknown code falls back to berawan."""
        url = get_icon_url(999, is_day=True)
        assert "berawan-am.svg" in url


class TestGetVisibilityText:
    """Test visibility text generation."""
    
    def test_greater_than_10km(self):
        """Visibility > 10km."""
        assert get_visibility_text(10000) == "> 10 km"
        assert get_visibility_text(15000) == "> 10 km"
    
    def test_between_5km_and_10km(self):
        """Visibility between 5km and 10km."""
        assert get_visibility_text(5000) == "5 km"
        assert get_visibility_text(8000) == "8 km"
    
    def test_between_1km_and_5km(self):
        """Visibility between 1km and 5km."""
        assert get_visibility_text(1000) == "1.0 km"
        assert get_visibility_text(2500) == "2.5 km"
    
    def test_less_than_1km(self):
        """Visibility < 1km."""
        assert get_visibility_text(500) == "500 m"
        assert get_visibility_text(900) == "900 m"


class TestParseLocation:
    """Test location parsing."""
    
    def test_parse_location_complete(self):
        """Parse complete location data."""
        data = {
            "adm4": "33.26.16.1001",
            "provinsi": "Jawa Tengah",
            "kabkota": "Kab. Pekalongan",
            "kecamatan": "Wiradesa",
            "deskel": "Kadipaten",
            "lat": -6.89,
            "lon": 109.67,
            "timezone": "+0700",
        }
        
        location = parse_location(data)
        
        assert isinstance(location, Location)
        assert location.code == "33.26.16.1001"
        assert location.province == "Jawa Tengah"
        assert location.district == "Kab. Pekalongan"
        assert location.subdistrict == "Wiradesa"
        assert location.village == "Kadipaten"
        assert location.lat == -6.89
        assert location.lon == 109.67
        assert location.timezone == "+0700"
    
    def test_parse_location_defaults(self):
        """Parse location with missing fields."""
        data = {
            "adm4": "33.26.16.1001",
            "lat": "-6.89",
            "lon": "109.67",
        }
        
        location = parse_location(data)
        
        assert location.code == "33.26.16.1001"
        assert location.province == ""
        assert location.lat == -6.89
        assert location.lon == 109.67


class TestParseForecastEntry:
    """Test forecast entry parsing."""
    
    def test_parse_complete_entry(self):
        """Parse complete forecast entry."""
        data = {
            "local_datetime": "2026-02-16 07:00:00",
            "utc_datetime": "2026-02-16 00:00:00",
            "t": 27,
            "hu": 83,
            "weather": 3,
            "ws": 7.3,
            "wd": "SW",
            "wd_deg": 266,
            "tcc": 100,
            "vs": 32349,
        }
        
        entry = parse_forecast_entry(data)
        
        assert isinstance(entry, ForecastEntry)
        # Use model_dump(by_alias=True) to access aliased field values
        entry_data = entry.model_dump(by_alias=True)
        assert entry_data["local_datetime"] == "2026-02-16 07:00:00"
        assert entry_data["utc_datetime"] == "2026-02-16 00:00:00"
        assert entry.temperature_c == 27
        assert entry.humidity_pct == 83
        assert entry.weather == "Berawan Tebal"
        assert entry.weather_en == "Overcast"
        assert entry.weather_code == 3
        assert entry.wind_speed_kmh == 7.3
        assert entry.wind_direction == "SW"
        assert entry.wind_direction_deg == 266
        assert entry.cloud_cover_pct == 100
        assert entry.visibility_m == 32349
        assert entry.visibility_text == "> 10 km"
        assert "berawan-tebal-am.svg" in entry.icon_url
    
    def test_parse_night_entry(self):
        """Parse nighttime forecast entry."""
        data = {
            "local_datetime": "2026-02-16 22:00:00",
            "utc_datetime": "2026-02-16 15:00:00",
            "t": 25,
            "hu": 88,
            "weather": 5,
            "ws": 5.0,
            "wd": "S",
            "wd_deg": 180,
            "tcc": 100,
            "vs": 25000,
        }
        
        entry = parse_forecast_entry(data)
        
        entry_data = entry.model_dump(by_alias=True)
        assert entry_data["local_datetime"] == "2026-02-16 22:00:00"
        assert "hujan-ringan-pm.svg" in entry.icon_url  # Night icon
    
    def test_parse_invalid_entry_returns_none(self):
        """Invalid entry returns None."""
        data = {
            "local_datetime": "invalid",
            "weather": "not_a_number",
        }
        
        entry = parse_forecast_entry(data)
        
        assert entry is None


class TestGroupForecastByDate:
    """Test grouping forecast entries by date."""
    
    def test_group_single_day(self):
        """Group entries from single day."""
        entries = [
            ForecastEntry(
                datetime_local="2026-02-16 07:00:00",
                datetime_utc="2026-02-16 00:00:00",
                temperature_c=27,
                humidity_pct=80,
                weather="Cerah",
                weather_en="Clear",
                weather_code=0,
                wind_speed_kmh=5.0,
                wind_direction="N",
                wind_direction_deg=0,
                cloud_cover_pct=10,
                visibility_m=35000,
                visibility_text="> 10 km",
                icon_url="https://example.com/icon.svg",
            ),
            ForecastEntry(
                datetime_local="2026-02-16 13:00:00",
                datetime_utc="2026-02-16 06:00:00",
                temperature_c=30,
                humidity_pct=70,
                weather="Cerah",
                weather_en="Clear",
                weather_code=0,
                wind_speed_kmh=5.0,
                wind_direction="N",
                wind_direction_deg=0,
                cloud_cover_pct=10,
                visibility_m=35000,
                visibility_text="> 10 km",
                icon_url="https://example.com/icon.svg",
            ),
        ]
        
        days = group_forecast_by_date(entries)
        
        assert len(days) == 1
        assert days[0].date == "2026-02-16"
        assert len(days[0].entries) == 2
    
    def test_group_multiple_days(self):
        """Group entries from multiple days."""
        entries = [
            ForecastEntry(
                datetime_local="2026-02-17 07:00:00",
                datetime_utc="2026-02-17 00:00:00",
                temperature_c=26,
                humidity_pct=85,
                weather="Berawan",
                weather_en="Mostly Cloudy",
                weather_code=2,
                wind_speed_kmh=6.0,
                wind_direction="E",
                wind_direction_deg=90,
                cloud_cover_pct=80,
                visibility_m=30000,
                visibility_text="> 10 km",
                icon_url="https://example.com/icon.svg",
            ),
            ForecastEntry(
                datetime_local="2026-02-16 07:00:00",
                datetime_utc="2026-02-16 00:00:00",
                temperature_c=27,
                humidity_pct=80,
                weather="Cerah",
                weather_en="Clear",
                weather_code=0,
                wind_speed_kmh=5.0,
                wind_direction="N",
                wind_direction_deg=0,
                cloud_cover_pct=10,
                visibility_m=35000,
                visibility_text="> 10 km",
                icon_url="https://example.com/icon.svg",
            ),
        ]
        
        days = group_forecast_by_date(entries)
        
        assert len(days) == 2
        # Should be sorted by date
        assert days[0].date == "2026-02-16"
        assert days[1].date == "2026-02-17"


class TestParseWeatherForecast:
    """Test complete forecast parsing."""
    
    def test_parse_forecast_response(self, load_fixture):
        """Parse complete BMKG forecast response."""
        data = load_fixture("forecast_response.json")
        
        forecast = parse_weather_forecast(data)
        
        assert isinstance(forecast, WeatherForecast)
        assert forecast.location.code == "33.26.16.1001"
        assert forecast.location.province == "Jawa Tengah"
        assert forecast.location.district == "Kab. Pekalongan"
        assert forecast.location.subdistrict == "Wiradesa"
        assert forecast.location.village == "Kadipaten"
        
        # Should have multiple days
        assert len(forecast.forecast) >= 1
        
        # First day should have entries
        assert len(forecast.forecast[0].entries) > 0
        
        # Check first entry
        first_entry = forecast.forecast[0].entries[0]
        assert first_entry.temperature_c == 27
        assert first_entry.humidity_pct == 83
        assert first_entry.weather_code == 3
    
    def test_parse_error_response(self):
        """Parse error response raises ValueError."""
        data = {
            "status": "error",
            "message": "Kode wilayah tidak ditemukan"
        }
        
        with pytest.raises(ValueError, match="Kode wilayah tidak ditemukan"):
            parse_weather_forecast(data)
    
    def test_parse_empty_data(self):
        """Parse empty data raises ValueError."""
        data = {
            "lokasi": {
                "adm4": "33.26.16.1001",
                "lat": -6.89,
                "lon": 109.67,
            },
            "data": []
        }
        
        with pytest.raises(ValueError, match="No forecast entries found"):
            parse_weather_forecast(data)


class TestFindCurrentForecast:
    """Test finding current forecast entry."""
    
    def test_find_current_returns_entry(self):
        """Find current returns a forecast entry."""
        # Create a forecast with future dates (so it finds first entry)
        future_year = datetime.now().year + 1
        forecast = WeatherForecast(
            location=Location(
                code="33.26.16.1001",
                province="Test",
                district="Test",
                subdistrict="Test",
                village="Test",
                lat=0.0,
                lon=0.0,
                timezone="+0700",
            ),
            forecast=[
                ForecastDay(
                    date=f"{future_year}-02-16",
                    entries=[
                        ForecastEntry(
                            datetime_local=f"{future_year}-02-16 07:00:00",
                            datetime_utc=f"{future_year}-02-16 00:00:00",
                            temperature_c=27,
                            humidity_pct=80,
                            weather="Cerah",
                            weather_en="Clear",
                            weather_code=0,
                            wind_speed_kmh=5.0,
                            wind_direction="N",
                            wind_direction_deg=0,
                            cloud_cover_pct=10,
                            visibility_m=35000,
                            visibility_text="> 10 km",
                            icon_url="https://example.com/icon.svg",
                        ),
                    ],
                ),
            ],
        )
        
        current = find_current_forecast(forecast)
        
        assert isinstance(current, ForecastEntry)
        assert current.temperature_c == 27
    
    def test_find_current_empty_forecast(self):
        """Empty forecast returns None."""
        forecast = WeatherForecast(
            location=Location(
                code="33.26.16.1001",
                province="Test",
                district="Test",
                subdistrict="Test",
                village="Test",
                lat=0.0,
                lon=0.0,
                timezone="+0700",
            ),
            forecast=[],
        )
        
        current = find_current_forecast(forecast)
        
        assert current is None


class TestWeatherModel:
    """Test Weather Pydantic models."""
    
    def test_location_model_dump(self):
        """Test Location model serialization."""
        location = Location(
            code="33.26.16.1001",
            province="Jawa Tengah",
            district="Kab. Pekalongan",
            subdistrict="Wiradesa",
            village="Kadipaten",
            lat=-6.89,
            lon=109.67,
            timezone="+0700",
        )
        
        data = location.model_dump()
        assert data["code"] == "33.26.16.1001"
        assert data["province"] == "Jawa Tengah"
        assert data["lat"] == -6.89
    
    def test_forecast_entry_model(self):
        """Test ForecastEntry model."""
        entry = ForecastEntry(
            datetime_local="2026-02-16 07:00:00",
            datetime_utc="2026-02-16 00:00:00",
            temperature_c=27,
            humidity_pct=83,
            weather="Berawan",
            weather_en="Mostly Cloudy",
            weather_code=2,
            wind_speed_kmh=7.3,
            wind_direction="SW",
            wind_direction_deg=266,
            cloud_cover_pct=100,
            visibility_m=32349,
            visibility_text="> 10 km",
            icon_url="https://example.com/icon.svg",
        )
        
        data = entry.model_dump(by_alias=True)
        assert "local_datetime" in data
        assert "utc_datetime" in data
        assert data["temperature_c"] == 27
