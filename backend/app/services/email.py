"""Email delivery abstraction.

One interface, several providers. Development writes to the log (``console``),
staging/production can use SMTP, SendGrid, Amazon SES or Resend by changing
``EMAIL_PROVIDER`` and ``EMAIL_API_KEY`` - no code change.
"""
from __future__ import annotations

import abc
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("email")


@dataclass(slots=True)
class EmailMessagePayload:
    to: str
    subject: str
    html: str
    text: str
    template: str = "generic"


class EmailProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def send(self, message: EmailMessagePayload) -> None: ...


class ConsoleEmailProvider(EmailProvider):
    """Development default - logs the email instead of sending it."""

    name = "console"

    async def send(self, message: EmailMessagePayload) -> None:
        log.info(
            "email.console",
            to=message.to, subject=message.subject, template=message.template,
            preview=message.text[:400],
        )


class SMTPEmailProvider(EmailProvider):
    name = "smtp"

    async def send(self, message: EmailMessagePayload) -> None:
        import asyncio

        def _send() -> None:
            msg = EmailMessage()
            msg["Subject"] = message.subject
            msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg["To"] = message.to
            msg.set_content(message.text)
            msg.add_alternative(message.html, subtype="html")
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_TLS:
                    server.starttls(context=ssl.create_default_context())
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

        await asyncio.to_thread(_send)


class SendGridEmailProvider(EmailProvider):
    name = "sendgrid"

    async def send(self, message: EmailMessagePayload) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"},
                json={
                    "personalizations": [{"to": [{"email": message.to}]}],
                    "from": {"email": settings.EMAIL_FROM, "name": settings.EMAIL_FROM_NAME},
                    "subject": message.subject,
                    "content": [
                        {"type": "text/plain", "value": message.text},
                        {"type": "text/html", "value": message.html},
                    ],
                },
            )
            response.raise_for_status()


class ResendEmailProvider(EmailProvider):
    name = "resend"

    async def send(self, message: EmailMessagePayload) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"},
                json={
                    "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                    "to": [message.to],
                    "subject": message.subject,
                    "html": message.html,
                    "text": message.text,
                },
            )
            response.raise_for_status()


class SESEmailProvider(EmailProvider):
    """Amazon SES through boto3 (imported lazily so boto3 stays optional)."""

    name = "ses"

    async def send(self, message: EmailMessagePayload) -> None:
        import asyncio

        def _send() -> None:
            import boto3  # type: ignore[import-untyped]

            client = boto3.client(
                "ses",
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.S3_ACCESS_KEY or None,
                aws_secret_access_key=settings.S3_SECRET_KEY or None,
            )
            client.send_email(
                Source=f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                Destination={"ToAddresses": [message.to]},
                Message={
                    "Subject": {"Data": message.subject},
                    "Body": {
                        "Text": {"Data": message.text},
                        "Html": {"Data": message.html},
                    },
                },
            )

        await asyncio.to_thread(_send)


_PROVIDERS: dict[str, type[EmailProvider]] = {
    "console": ConsoleEmailProvider,
    "smtp": SMTPEmailProvider,
    "sendgrid": SendGridEmailProvider,
    "ses": SESEmailProvider,
    "resend": ResendEmailProvider,
}


def get_provider() -> EmailProvider:
    return _PROVIDERS.get(settings.EMAIL_PROVIDER, ConsoleEmailProvider)()


# ------------------------------------------------------------- templates ----
_BASE_HTML = """<!doctype html>
<html><body style="margin:0;padding:0;background:#f5f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:14px;border:1px solid #e6e8ec;overflow:hidden;">
        <tr><td style="padding:24px 28px;border-bottom:1px solid #eef0f3;">
          <span style="font-size:17px;font-weight:700;color:#0f172a;letter-spacing:-0.2px;">SkillBridge</span>
          <span style="font-size:12px;color:#64748b;"> &nbsp;·&nbsp; Academia–Industry Employability Platform</span>
        </td></tr>
        <tr><td style="padding:28px;color:#334155;font-size:15px;line-height:1.6;">
          <h1 style="margin:0 0 14px;font-size:20px;color:#0f172a;">{heading}</h1>
          {body}
        </td></tr>
        <tr><td style="padding:18px 28px;background:#fafbfc;border-top:1px solid #eef0f3;color:#94a3b8;font-size:12px;line-height:1.5;">
          You are receiving this because you have a SkillBridge account.<br/>
          Manage what we send you in Settings &rsaquo; Notifications.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _button(url: str, label: str) -> str:
    return (
        f'<p style="margin:22px 0;"><a href="{url}" '
        'style="display:inline-block;background:#1c5d99;color:#ffffff;text-decoration:none;'
        'padding:11px 20px;border-radius:8px;font-weight:600;font-size:14px;">'
        f"{label}</a></p>"
    )


def render(template: str, **ctx: Any) -> tuple[str, str, str]:
    """Return ``(subject, html, text)`` for a named template."""
    app_url = settings.FRONTEND_URL
    name = ctx.get("name", "there")

    if template == "welcome":
        subject = "Welcome to SkillBridge"
        body = (
            f"<p>Hi {name},</p><p>Your SkillBridge account is ready. Start by completing "
            "your profile and taking a skill assessment - that is what powers your "
            "personalised role recommendations and skill-gap analysis.</p>"
            + _button(f"{app_url}/student/dashboard", "Open your dashboard")
        )
        text = f"Hi {name}, your SkillBridge account is ready. Open {app_url}"
        heading = "Welcome aboard"

    elif template == "verify_email":
        url = ctx["verify_url"]
        subject = "Verify your SkillBridge email address"
        body = (
            f"<p>Hi {name},</p><p>Confirm this email address to activate your account. "
            f"This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours.</p>"
            + _button(url, "Verify email address")
            + f'<p style="font-size:12px;color:#64748b;word-break:break-all;">{url}</p>'
        )
        text = f"Verify your SkillBridge email: {url}"
        heading = "Verify your email"

    elif template == "reset_password":
        url = ctx["reset_url"]
        subject = "Reset your SkillBridge password"
        body = (
            f"<p>Hi {name},</p><p>We received a request to reset your password. "
            f"This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes. "
            "If you did not request it, you can safely ignore this email - your "
            "password will not change.</p>" + _button(url, "Choose a new password")
            + f'<p style="font-size:12px;color:#64748b;word-break:break-all;">{url}</p>'
        )
        text = f"Reset your SkillBridge password: {url}"
        heading = "Password reset"

    elif template == "password_changed":
        subject = "Your SkillBridge password was changed"
        body = (
            f"<p>Hi {name},</p><p>Your password was just changed and all other active "
            "sessions were signed out. If this was not you, reset your password "
            "immediately and contact your institution administrator.</p>"
            + _button(f"{app_url}/forgot-password", "Reset password")
        )
        text = "Your SkillBridge password was changed."
        heading = "Password changed"

    elif template == "application_update":
        subject = f"Update on your application: {ctx['opportunity_title']}"
        body = (
            f"<p>Hi {name},</p><p>Your application for <strong>{ctx['opportunity_title']}</strong> "
            f"at <strong>{ctx['company_name']}</strong> moved to "
            f"<strong>{ctx['status']}</strong>.</p>"
            + (f"<p>{ctx['note']}</p>" if ctx.get("note") else "")
            + _button(f"{app_url}/student/applications", "Track your application")
        )
        text = f"Your application for {ctx['opportunity_title']} is now {ctx['status']}."
        heading = "Application update"

    elif template == "interview_invitation":
        subject = f"Interview scheduled: {ctx['opportunity_title']}"
        body = (
            f"<p>Hi {name},</p><p><strong>{ctx['company_name']}</strong> has scheduled your "
            f"<strong>{ctx['round_name']}</strong> for "
            f"<strong>{ctx['scheduled_at']}</strong> ({ctx['duration']} minutes).</p>"
            + (f"<p>Where: {ctx['location']}</p>" if ctx.get("location") else "")
            + (f"<p>{ctx['instructions']}</p>" if ctx.get("instructions") else "")
            + _button(f"{app_url}/student/applications", "View details")
        )
        text = f"Interview for {ctx['opportunity_title']} on {ctx['scheduled_at']}."
        heading = "You have an interview"

    elif template == "selection":
        subject = f"Congratulations - selected for {ctx['opportunity_title']}"
        body = (
            f"<p>Hi {name},</p><p>You have been selected for "
            f"<strong>{ctx['opportunity_title']}</strong> at "
            f"<strong>{ctx['company_name']}</strong>. Well done.</p>"
            + _button(f"{app_url}/student/applications", "See next steps")
        )
        text = f"You have been selected for {ctx['opportunity_title']}."
        heading = "You're selected"

    elif template == "rejection":
        subject = f"Update on your application: {ctx['opportunity_title']}"
        body = (
            f"<p>Hi {name},</p><p>Thank you for applying to "
            f"<strong>{ctx['opportunity_title']}</strong> at {ctx['company_name']}. "
            "The team has decided not to move forward this time.</p>"
            "<p>Your skill-gap report shows exactly which skills would strengthen "
            "your next application for this kind of role.</p>"
            + _button(f"{app_url}/student/skill-gap", "See your skill gaps")
        )
        text = f"Your application for {ctx['opportunity_title']} was not successful."
        heading = "Application update"

    elif template == "event_reminder":
        subject = f"Reminder: {ctx['event_title']}"
        body = (
            f"<p>Hi {name},</p><p><strong>{ctx['event_title']}</strong> starts "
            f"{ctx['starts_at']}.</p>"
            + (f"<p>Join: {ctx['link']}</p>" if ctx.get("link") else "")
            + _button(f"{app_url}/student/workshops", "View event")
        )
        text = f"{ctx['event_title']} starts {ctx['starts_at']}."
        heading = "Event reminder"

    elif template == "mentorship_request":
        subject = f"New mentorship request from {ctx['student_name']}"
        body = (
            f"<p>Hi {name},</p><p><strong>{ctx['student_name']}</strong> has requested "
            f"mentorship on <strong>{ctx['topic']}</strong>.</p>"
            + _button(f"{app_url}/mentorship/requests", "Review request")
        )
        text = f"{ctx['student_name']} requested mentorship on {ctx['topic']}."
        heading = "Mentorship request"

    else:
        subject = ctx.get("subject", "SkillBridge notification")
        body = f"<p>{ctx.get('body', '')}</p>"
        text = ctx.get("body", "")
        heading = ctx.get("heading", "Notification")

    return subject, _BASE_HTML.format(heading=heading, body=body), text


async def send_email(
    to: str, template: str, *, db: Any = None, user_id: uuid.UUID | None = None, **ctx: Any
) -> bool:
    """Render and deliver a template. Never raises - failures are logged."""
    subject, html, text = render(template, **ctx)
    payload = EmailMessagePayload(
        to=to, subject=subject, html=html, text=text, template=template
    )
    provider = get_provider()
    status, error = "SENT", None
    try:
        await provider.send(payload)
    except Exception as exc:  # pragma: no cover - network dependent
        status, error = "FAILED", str(exc)[:500]
        log.error("email.failed", to=to, template=template, error=error)

    if db is not None:
        from app.models.notification import EmailLog

        db.add(
            EmailLog(
                to_email=to, template=template, subject=subject, provider=provider.name,
                status=status, error=error,
                sent_at=datetime.now(UTC) if status == "SENT" else None,
                user_id=user_id,
            )
        )
    return status == "SENT"
