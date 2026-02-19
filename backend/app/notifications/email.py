"""Email SMTP notification sender."""

from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib
import structlog

from app.config import settings
from app.models import MatchResult, WarningInfo

logger = structlog.get_logger()

SEVERITY_COLOR = {
    "Minor": "#3B82F6",
    "Moderate": "#EAB308",
    "Severe": "#EF4444",
    "Extreme": "#1F2937",
}


class EmailSender:
    """Sends alert messages via SMTP email."""

    async def send(
        self,
        warning: WarningInfo,
        match: MatchResult,
        channel_config: dict[str, Any],
        is_trial: bool = False,
    ) -> bool:
        to_email = channel_config.get("to_email", "")
        if not to_email:
            logger.error("email_missing_to_email")
            return False

        smtp = self._resolve_smtp(channel_config)
        if not smtp["host"] or not smtp["user"]:
            logger.error("email_smtp_not_configured")
            return False

        subject, html_body = self._build_email(warning, match, is_trial)
        return await self._send_smtp(to_email, subject, html_body, smtp=smtp)

    async def send_raw(
        self, to_email: str, subject: str, body: str,
        channel_config: dict[str, Any] | None = None,
    ) -> bool:
        """Send a plain text email."""
        smtp = self._resolve_smtp(channel_config or {})
        return await self._send_smtp(to_email, subject, body, is_html=False, smtp=smtp)

    def _resolve_smtp(self, channel_config: dict[str, Any]) -> dict[str, Any]:
        """Resolve SMTP settings: channel config overrides env vars."""
        return {
            "host": channel_config.get("smtp_host") or settings.smtp_host or "",
            "port": int(channel_config.get("smtp_port") or settings.smtp_port or 587),
            "user": channel_config.get("smtp_user") or settings.smtp_user or "",
            "password": channel_config.get("smtp_password") or settings.smtp_password or "",
            "from_addr": settings.smtp_from,
        }

    def _build_email(
        self, warning: WarningInfo, match: MatchResult, is_trial: bool
    ) -> tuple[str, str]:
        loc = match.location
        color = SEVERITY_COLOR.get(warning.severity, "#6B7280")
        location_name = loc.label or loc.subdistrict_name

        subject = f"[BMKG Alert] {warning.severity}: {warning.event} — {location_name}"

        description = warning.description or warning.headline or ""
        if len(description) > 500:
            description = description[:497] + "..."

        infographic_html = ""
        if warning.infographic_url:
            infographic_html = (
                f'<p><a href="{warning.infographic_url}" '
                f'style="color:#2563EB;">Lihat Infografis BMKG</a></p>'
            )

        trial_html = ""
        if is_trial:
            trial_html = (
                '<p style="color:#6B7280;font-size:12px;margin-top:16px;">'
                'Mode Trial — notifikasi aktif sementara.</p>'
            )

        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:{color};color:white;padding:16px 20px;border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">Peringatan Cuaca — {warning.event}</h2>
                <p style="margin:4px 0 0;opacity:0.9;">{warning.severity}</p>
            </div>
            <div style="border:1px solid #E5E7EB;border-top:none;padding:20px;border-radius:0 0 8px 8px;">
                <table style="width:100%;font-size:14px;border-collapse:collapse;">
                    <tr>
                        <td style="padding:6px 0;color:#6B7280;width:120px;">Lokasi</td>
                        <td style="padding:6px 0;font-weight:600;">{location_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#6B7280;">Wilayah</td>
                        <td style="padding:6px 0;">{loc.subdistrict_name}, {loc.district_name}, {loc.province_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#6B7280;">Berlaku</td>
                        <td style="padding:6px 0;">{warning.effective or '-'}</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#6B7280;">Hingga</td>
                        <td style="padding:6px 0;">{warning.expires or '-'}</td>
                    </tr>
                </table>
                <p style="margin-top:16px;color:#374151;">{description}</p>
                {infographic_html}
                {trial_html}
                <hr style="border:none;border-top:1px solid #E5E7EB;margin:16px 0;" />
                <p style="font-size:12px;color:#9CA3AF;">
                    Sumber: BMKG (bmkg.go.id) | BMKG Alert System v1.0
                </p>
            </div>
        </div>
        """

        return subject, html

    async def _send_smtp(
        self, to_email: str, subject: str, body: str,
        is_html: bool = True, smtp: dict[str, Any] | None = None,
    ) -> bool:
        if smtp is None:
            smtp = self._resolve_smtp({})
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = smtp["from_addr"]
            msg["To"] = to_email
            msg["Subject"] = subject

            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            port = smtp["port"]
            await aiosmtplib.send(
                msg,
                hostname=smtp["host"],
                port=port,
                username=smtp["user"],
                password=smtp["password"],
                use_tls=port == 465,
                start_tls=port == 587,
            )

            logger.info("email_sent", to=to_email)
            return True
        except Exception as exc:
            logger.error("email_send_error", error=str(exc), to=to_email)
            return False
