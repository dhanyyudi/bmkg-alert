"""Parser for BMKG earthquake JSON data."""

from datetime import datetime
from app.models.earthquake import Earthquake


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse BMKG datetime format to datetime object.
    
    BMKG format:
    - date: "16 Feb 2026"
    - time: "13:15:30 WIB" or "13:15:30 WITA" or "13:15:30 WIT"
    
    Returns UTC datetime.
    """
    # Parse date
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    
    day, month_abbr, year = date_str.split()
    month = months.get(month_abbr, 1)
    
    # Parse time and timezone
    time_parts = time_str.split()
    time_only = time_parts[0]
    tz_abbr = time_parts[1] if len(time_parts) > 1 else "WIB"
    
    # Timezone offset from UTC
    tz_offsets = {
        "WIB": 7,   # Western Indonesia Time (UTC+7)
        "WITA": 8,  # Central Indonesia Time (UTC+8)
        "WIT": 9,   # Eastern Indonesia Time (UTC+9)
    }
    
    offset_hours = tz_offsets.get(tz_abbr, 7)
    
    # Parse time components
    hour, minute, second = map(int, time_only.split(":"))
    
    # Create datetime in local timezone
    local_dt = datetime(
        int(year), month, int(day),
        hour, minute, second
    )
    
    # Convert to UTC by subtracting offset
    from datetime import timedelta
    utc_dt = local_dt - timedelta(hours=offset_hours)
    
    return utc_dt


def parse_coordinates(lat_str: str, lon_str: str) -> tuple[float, float, str, str]:
    """Parse BMKG coordinate strings to decimal degrees.
    
    BMKG format:
    - lat: "6.89 LU" or "6.89 LS" (LU=Lintang Utara/North, LS=Lintang Selatan/South)
    - lon: "109.67 BT" or "109.67 BB" (BT=Bujur Timur/East, BB=Bujur Barat/West)
    
    Returns (lat, lon, lat_text, lon_text)
    """
    # Parse latitude
    lat_parts = lat_str.split()
    lat_val = float(lat_parts[0])
    lat_dir = lat_parts[1] if len(lat_parts) > 1 else "LU"
    
    if lat_dir == "LS":  # South
        lat_val = -lat_val
    
    # Parse longitude
    lon_parts = lon_str.split()
    lon_val = float(lon_parts[0])
    lon_dir = lon_parts[1] if len(lon_parts) > 1 else "BT"
    
    if lon_dir == "BB":  # West
        lon_val = -lon_val
    
    return lat_val, lon_val, lat_str, lon_str


def parse_earthquake(data: dict) -> Earthquake:
    """Parse single earthquake from BMKG JSON.
    
    Args:
        data: Raw earthquake data from BMKG
        
    Returns:
        Parsed Earthquake model
    """
    # Parse datetime
    date_str = data.get("Tanggal", "")
    time_str = data.get("Jam", "")
    dt = parse_datetime(date_str, time_str)
    
    # Parse coordinates
    lat_str = data.get("Lintang", "")
    lon_str = data.get("Bujur", "")
    lat, lon, lat_text, lon_text = parse_coordinates(lat_str, lon_str)
    
    # Parse magnitude (handle formats like "5.4" or "5.4 SR")
    magnitude_str = data.get("Magnitude", "0")
    magnitude = float(magnitude_str.split()[0]) if magnitude_str else 0.0
    
    # Parse depth (handle format like "10 km")
    depth_str = data.get("Kedalaman", "0")
    depth = float(depth_str.split()[0]) if depth_str else 0.0
    
    # Build shakemap URL
    shakemap_url = None
    if "Shakemap" in data and data["Shakemap"]:
        shakemap_filename = data["Shakemap"]
        shakemap_url = f"https://data.bmkg.go.id/DataMKG/TEWS/{shakemap_filename}"
    
    return Earthquake(
        occurred_at=dt,
        magnitude=magnitude,
        depth_km=depth,
        lat=lat,
        lon=lon,
        lat_text=lat_text,
        lon_text=lon_text,
        region=data.get("Wilayah", ""),
        tsunami_potential=data.get("Potensi", None),
        felt_report=data.get("Dirasakan", None),
        shakemap_url=shakemap_url,
    )


def parse_earthquake_list(data: dict) -> list[Earthquake]:
    """Parse list of earthquakes from BMKG JSON.
    
    Args:
        data: Raw BMKG response with InfoGempa or similar structure
        
    Returns:
        List of parsed Earthquake models
    """
    earthquakes = []
    
    # Handle different response structures
    if "Infogempa" in data:
        info = data["Infogempa"]
        
        # Single earthquake (autogempa)
        if "gempa" in info:
            gempa_data = info["gempa"]
            if isinstance(gempa_data, dict):
                earthquakes.append(parse_earthquake(gempa_data))
            elif isinstance(gempa_data, list):
                for eq_data in gempa_data:
                    earthquakes.append(parse_earthquake(eq_data))
    
    return earthquakes
