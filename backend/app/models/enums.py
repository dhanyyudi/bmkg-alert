"""Enum definitions for the BMKG API."""

from enum import Enum


class _ValueStrEnum(str, Enum):
    """str-backed enum whose str()/format() is its value, as StrEnum does."""

    def __str__(self) -> str:
        return str(self.value)


class Severity(_ValueStrEnum):
    """CAP severity levels."""
    EXTREME = "Extreme"
    SEVERE = "Severe"
    MODERATE = "Moderate"
    MINOR = "Minor"
    UNKNOWN = "Unknown"


class Urgency(_ValueStrEnum):
    """CAP urgency levels."""
    IMMEDIATE = "Immediate"
    EXPECTED = "Expected"
    FUTURE = "Future"
    PAST = "Past"
    UNKNOWN = "Unknown"


class Certainty(_ValueStrEnum):
    """CAP certainty levels."""
    OBSERVED = "Observed"
    LIKELY = "Likely"
    POSSIBLE = "Possible"
    UNLIKELY = "Unlikely"
    UNKNOWN = "Unknown"
