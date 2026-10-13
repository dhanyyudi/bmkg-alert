"""Telegram notification formatter — builds rich alert messages."""

from __future__ import annotations

from html import escape

from app.models import MatchResult, WarningInfo

# Severity emoji mapping
SEVERITY_EMOJI = {
    "Minor": "🔵",
    "Moderate": "🟡",
    "Severe": "🔴",
    "Extreme": "⚫",
}


SEVERITY_LABEL = {
    "Minor": "Ringan",
    "Moderate": "Sedang",
    "Severe": "Berat",
    "Extreme": "Ekstrem",
}


def severity_label(severity) -> str:
    """Indonesian name for a CAP severity level, as shown in the dashboard."""
    value = str(getattr(severity, "value", severity))
    return SEVERITY_LABEL.get(value, value)


def format_telegram_message(
    warning: WarningInfo,
    match: MatchResult,
    is_trial: bool = False,
) -> str:
    """Format a warning into a Telegram message string (HTML parse mode).

    Args:
        warning: The BMKG warning details.
        match: The match result with location info.
        is_trial: Whether this is a trial subscription message.

    Returns:
        HTML-formatted message string for Telegram sendMessage.
    """
    emoji = SEVERITY_EMOJI.get(str(warning.severity), "⚠️")
    location = match.location

    # Telegram parses this as HTML, so text from BMKG and from the user is escaped
    lines = [
        f"{emoji} <b>Peringatan Cuaca: {escape(warning.event)}</b>",
        "",
        f"📍 <b>Lokasi terpantau:</b> {escape(location.label or location.subdistrict_name)}",
        f"   {escape(location.subdistrict_name)}, {escape(location.district_name)}, {escape(location.province_name)}",
        "",
        f"⚡ <b>Tingkat:</b> {severity_label(warning.severity)}",
        f"🕐 <b>Berlaku:</b> {format_time(warning.effective)}",
        f"⏰ <b>Hingga:</b> {format_time(warning.expires)}",
    ]

    # Add description (truncated for Telegram)
    if warning.description:
        desc = warning.description
        if len(desc) > 500:
            desc = desc[:497] + "..."
        lines.extend(["", f"📝 {escape(desc)}"])

    # Add match info
    lines.extend([
        "",
        f"🔍 <i>Cocok dengan {escape(match.match_type)} {escape(match.matched_text)}</i>",
    ])

    # Add infographic link
    if warning.infographic_url:
        lines.extend([
            "",
            f"🗺️ <a href=\"{escape(warning.infographic_url, quote=True)}\">Lihat infografis BMKG</a>",
        ])

    # Trial mode footer
    if is_trial:
        lines.extend([
            "",
            "⏳ <i>Mode trial: notifikasi aktif selama 24 jam.</i>",
        ])

    # Attribution
    lines.extend([
        "",
        "📡 Sumber: BMKG (bmkg.go.id)",
    ])

    return "\n".join(lines)


def format_time(iso_str) -> str:
    """Format ISO timestamp to a human-readable Indonesian time string."""
    if not iso_str:
        return "-"
    # Accept datetime objects as well as ISO strings
    if hasattr(iso_str, 'isoformat'):
        iso_str = iso_str.isoformat()
    # Parse and format — the BMKG API already includes timezone offset
    # We just clean it up for display
    try:
        # Remove the timezone offset for cleaner display
        # Input: "2026-02-17T19:55:00+07:00"
        if "T" in iso_str:
            date_part, time_part = iso_str.split("T")
            # Get time without timezone
            time_clean = time_part[:5]  # "19:55"
            # Determine timezone label
            tz_label = "WIB"
            if "+08" in time_part:
                tz_label = "WITA"
            elif "+09" in time_part:
                tz_label = "WIT"
            return f"{date_part} {time_clean} {tz_label}"
    except (ValueError, IndexError):
        pass
    return iso_str


# Kept for callers and tests that still use the private name
_format_time = format_time
