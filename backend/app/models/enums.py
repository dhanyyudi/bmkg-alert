"""Enum definitions for the BMKG API."""

from enum import Enum


class Severity(str, Enum):
    """CAP severity levels."""
    EXTREME = "Extreme"
    SEVERE = "Severe"
    MODERATE = "Moderate"
    MINOR = "Minor"
    UNKNOWN = "Unknown"


class Urgency(str, Enum):
    """CAP urgency levels."""
    IMMEDIATE = "Immediate"
    EXPECTED = "Expected"
    FUTURE = "Future"
    PAST = "Past"
    UNKNOWN = "Unknown"


class Certainty(str, Enum):
    """CAP certainty levels."""
    OBSERVED = "Observed"
    LIKELY = "Likely"
    POSSIBLE = "Possible"
    UNLIKELY = "Unlikely"
    UNKNOWN = "Unknown"


class WeatherCode(int, Enum):
    """BMKG weather condition codes."""
    CERAH = 0
    CERAH_BERAWAN = 1
    BERAWAN = 2
    BERAWAN_TEBAL = 3
    KABUT = 4
    HUJAN_RINGAN = 5
    HUJAN_SEDANG = 10
    HUJAN_LEBAT = 45
    HUJAN_LOKAL = 60
    PETIR = 95
    PETIR_DAN_HUJAN_LEBAT = 97


# Weather code to name mapping
WEATHER_CODE_NAMES = {
    0: ("Cerah", "Clear"),
    1: ("Cerah Berawan", "Partly Cloudy"),
    2: ("Berawan", "Mostly Cloudy"),
    3: ("Berawan Tebal", "Overcast"),
    4: ("Kabut", "Haze"),
    5: ("Hujan Ringan", "Light Rain"),
    10: ("Hujan Sedang", "Moderate Rain"),
    45: ("Hujan Lebat", "Heavy Rain"),
    60: ("Hujan Lokal", "Local Rain"),
    95: ("Petir", "Thunderstorm"),
    97: ("Petir dan Hujan Lebat", "Severe Thunderstorm"),
}
