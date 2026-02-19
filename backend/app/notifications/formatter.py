"""Telegram notification formatter — builds rich alert messages."""

from __future__ import annotations

from app.models import MatchResult, WarningInfo

# Severity emoji mapping
SEVERITY_EMOJI = {
    "Minor": "🔵",
    "Moderate": "🟡",
    "Severe": "🔴",
    "Extreme": "⚫",
}


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
    emoji = SEVERITY_EMOJI.get(warning.severity, "⚠️")
    location = match.location

    # Build header
    lines = [
        f"{emoji} <b>Peringatan Cuaca — {warning.event}</b>",
        "",
        f"📍 <b>Lokasi Terpantau:</b> {location.label or location.subdistrict_name}",
        f"   {location.subdistrict_name}, {location.district_name}, {location.province_name}",
        "",
        f"⚡ <b>Tingkat:</b> {warning.severity}",
        f"🕐 <b>Berlaku:</b> {_format_time(warning.effective)}",
        f"⏰ <b>Hingga:</b> {_format_time(warning.expires)}",
    ]

    # Add description (truncated for Telegram)
    if warning.description:
        desc = warning.description
        if len(desc) > 500:
            desc = desc[:497] + "..."
        lines.extend(["", f"📝 {desc}"])

    # Add match info
    lines.extend([
        "",
        f"🔍 <i>Cocok: {match.match_type} — {match.matched_text}</i>",
    ])

    # Add infographic link
    if warning.infographic_url:
        lines.extend([
            "",
            f"🗺️ <a href=\"{warning.infographic_url}\">Lihat Infografis BMKG</a>",
        ])

    # Trial mode footer
    if is_trial:
        lines.extend([
            "",
            "─" * 30,
            "⏳ <i>Mode Trial — langganan aktif selama 7 hari.</i>",
        ])

    # Attribution
    lines.extend([
        "",
        "─" * 30,
        "📡 Sumber: BMKG (bmkg.go.id)",
        "🤖 BMKG Alert System v1.0",
    ])

    return "\n".join(lines)


def format_expiry_message(
    warning_event: str,
    location_label: str,
) -> str:
    """Format an 'all clear' message when a warning expires."""
    return (
        f"✅ <b>Peringatan Berakhir</b>\n"
        f"\n"
        f"Peringatan <b>{warning_event}</b> untuk "
        f"<b>{location_label}</b> telah berakhir.\n"
        f"\n"
        f"Kondisi sudah aman. Tetap waspada.\n"
        f"\n"
        f"📡 Sumber: BMKG (bmkg.go.id)"
    )


def _format_time(iso_str: str) -> str:
    """Format ISO timestamp to a human-readable Indonesian time string."""
    if not iso_str:
        return "-"
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
