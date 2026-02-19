"""Parser for BMKG weather forecast JSON data."""

from datetime import datetime, timezone
from app.models.weather import Location, ForecastEntry, ForecastDay, WeatherForecast
from app.models.enums import WEATHER_CODE_NAMES


def get_icon_url(weather_code: int, is_day: bool = True) -> str:
    """Generate icon URL from weather code.
    
    Args:
        weather_code: BMKG weather code
        is_day: Whether it's daytime (affects icon variant)
        
    Returns:
        URL to weather icon
    """
    # Map weather codes to icon names
    icon_map = {
        0: "cerah",
        1: "cerah-berawan",
        2: "berawan",
        3: "berawan-tebal",
        4: "kabut",
        5: "hujan-ringan",
        10: "hujan-sedang",
        45: "hujan-lebat",
        60: "hujan-lokal",
        95: "petir",
        97: "petir-hujan-lebat",
    }
    
    icon_name = icon_map.get(weather_code, "berawan")
    time_suffix = "-am" if is_day else "-pm"
    
    return f"https://api-apps.bmkg.go.id/storage/icon/cuaca/{icon_name}{time_suffix}.svg"


def get_visibility_text(visibility_m: int) -> str:
    """Convert visibility in meters to human-readable text.
    
    Args:
        visibility_m: Visibility in meters
        
    Returns:
        Human-readable visibility text
    """
    if visibility_m >= 10000:
        return "> 10 km"
    elif visibility_m >= 5000:
        return f"{visibility_m // 1000} km"
    elif visibility_m >= 1000:
        return f"{visibility_m / 1000:.1f} km"
    else:
        return f"{visibility_m} m"


def parse_location(data: dict) -> Location:
    """Parse location information from BMKG response.
    
    Args:
        data: Raw location data from BMKG
        
    Returns:
        Parsed Location model
    """
    return Location(
        code=data.get("adm4", ""),
        province=data.get("provinsi", ""),
        district=data.get("kabkota", ""),
        subdistrict=data.get("kecamatan", ""),
        village=data.get("deskel", ""),
        lat=float(data.get("lat", 0)),
        lon=float(data.get("lon", 0)),
        timezone=data.get("timezone", "+0700"),
    )


def parse_forecast_entry(entry_data: dict, timezone_offset: str = "+0700") -> ForecastEntry | None:
    """Parse a single forecast entry from BMKG data.
    
    Args:
        entry_data: Raw forecast entry data
        timezone_offset: Timezone offset string (e.g., "+0700")
        
    Returns:
        Parsed ForecastEntry model or None if parsing fails
    """
    try:
        # Parse local datetime
        local_datetime = entry_data.get("local_datetime", "")
        utc_datetime = entry_data.get("utc_datetime", "")
        
        # Get weather code and names
        weather_code = int(entry_data.get("weather", 0))
        weather_name, weather_name_en = WEATHER_CODE_NAMES.get(
            weather_code, ("Berawan", "Mostly Cloudy")
        )
        
        # Determine if it's daytime (for icon selection)
        # Simple check: between 06:00 and 18:00
        is_day = True
        if local_datetime:
            try:
                hour = int(local_datetime.split()[1].split(":")[0])
                is_day = 6 <= hour < 18
            except (IndexError, ValueError):
                pass
        
        # Parse numeric values
        temperature = int(entry_data.get("t", 0))
        humidity = int(entry_data.get("hu", 0))
        
        # Parse wind data
        wind_speed = float(entry_data.get("ws", 0))
        wind_direction = entry_data.get("wd", "")
        wind_direction_deg = int(entry_data.get("wd_deg", 0))
        
        # Parse cloud cover and visibility
        cloud_cover = int(entry_data.get("tcc", 0))
        visibility = int(entry_data.get("vs", 0))
        visibility_text = get_visibility_text(visibility)
        
        # Get icon URL
        icon_url = get_icon_url(weather_code, is_day)
        
        return ForecastEntry(
            local_datetime=local_datetime,
            utc_datetime=utc_datetime,
            temperature_c=temperature,
            humidity_pct=humidity,
            weather=weather_name,
            weather_en=weather_name_en,
            weather_code=weather_code,
            wind_speed_kmh=wind_speed,
            wind_direction=wind_direction,
            wind_direction_deg=wind_direction_deg,
            cloud_cover_pct=cloud_cover,
            visibility_m=visibility,
            visibility_text=visibility_text,
            icon_url=icon_url,
        )
    except (ValueError, TypeError, KeyError) as e:
        # Return None if we can't parse this entry
        return None


def group_forecast_by_date(entries: list[ForecastEntry]) -> list[ForecastDay]:
    """Group forecast entries by date.
    
    Args:
        entries: List of forecast entries
        
    Returns:
        List of ForecastDay objects
    """
    days: dict[str, list[ForecastEntry]] = {}
    
    for entry in entries:
        # Extract date from datetime_local (format: "2026-02-16 07:00:00")
        # Use model_dump to get the aliased field name value
        entry_data = entry.model_dump(by_alias=True)
        local_dt = entry_data.get("local_datetime", "")
        date = local_dt.split()[0] if local_dt else ""
        if date:
            if date not in days:
                days[date] = []
            days[date].append(entry)
    
    # Sort dates and create ForecastDay objects
    forecast_days = []
    for date in sorted(days.keys()):
        # Sort entries by datetime
        day_entries = sorted(days[date], key=lambda x: x.model_dump(by_alias=True).get("local_datetime", ""))
        forecast_days.append(ForecastDay(date=date, entries=day_entries))
    
    return forecast_days


def parse_weather_forecast(data: dict) -> WeatherForecast:
    """Parse complete weather forecast from BMKG response.
    
    Args:
        data: Raw BMKG weather forecast response
        
    Returns:
        Parsed WeatherForecast model
        
    Raises:
        ValueError: If data cannot be parsed
    """
    # Check for error response
    if "status" in data and data["status"] == "error":
        raise ValueError(data.get("message", "Unknown error from BMKG"))
    
    # Parse location
    location_data = data.get("lokasi", {})
    if not location_data:
        raise ValueError("No location data found in response")
    
    location = parse_location(location_data)
    
    # Parse forecast entries from BMKG nested structure:
    # data["data"][0]["cuaca"] = list of day-arrays, each containing forecast entries
    entries = []
    for group in data.get("data", []):
        for day_entries in group.get("cuaca", []):
            if isinstance(day_entries, list):
                for entry_data in day_entries:
                    entry = parse_forecast_entry(entry_data, location.timezone)
                    if entry:
                        entries.append(entry)
    
    if not entries:
        raise ValueError("No forecast entries found in response")
    
    # Group by date
    forecast_days = group_forecast_by_date(entries)
    
    return WeatherForecast(
        location=location,
        forecast=forecast_days,
    )


def find_current_forecast(forecast: WeatherForecast) -> ForecastEntry | None:
    """Find the current/n nearest forecast entry.
    
    Args:
        forecast: Weather forecast with multiple days
        
    Returns:
        The forecast entry closest to current time, or None if not found
    """
    now = datetime.now(timezone.utc)
    
    # Collect all entries with their datetime
    all_entries = []
    for day in forecast.forecast:
        for entry in day.entries:
            try:
                # Parse UTC datetime using model_dump to get aliased field
                entry_data = entry.model_dump(by_alias=True)
                utc_dt_str = entry_data.get("utc_datetime", "")
                entry_dt = datetime.strptime(
                    utc_dt_str, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                all_entries.append((entry_dt, entry))
            except (ValueError, TypeError):
                continue
    
    if not all_entries:
        # Fallback: return first entry of first day
        if forecast.forecast and forecast.forecast[0].entries:
            return forecast.forecast[0].entries[0]
        return None
    
    # Sort by time difference from now
    all_entries.sort(key=lambda x: abs((x[0] - now).total_seconds()))
    
    return all_entries[0][1]
