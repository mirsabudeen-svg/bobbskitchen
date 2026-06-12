"""
backend/app/services/whatsapp.py

Twilio WhatsApp service — Sprint 9
Responsibility: send the AI artwork PNG to the customer when their order
is marked ready. Single outbound message type, one trigger point.

Environment variables required:
    TWILIO_ACCOUNT_SID      — from console.twilio.com
    TWILIO_AUTH_TOKEN       — from console.twilio.com
    TWILIO_WHATSAPP_FROM    — your approved sender, e.g. whatsapp:+14155238886
    TWILIO_TEMPLATE_SID_EN  — approved template SID for English message
    TWILIO_TEMPLATE_SID_ML  — approved template SID for Malayalam message
    PUBLIC_MEDIA_BASE_URL   — publicly accessible base URL for artwork images
                              e.g. https://cdn.bobb.ai  (must be HTTPS, no auth)
"""

import logging
import re
from enum import Enum
from typing import Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwilioClient

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

class MessageLanguage(str, Enum):
    ENGLISH   = "en"
    MALAYALAM = "ml"


# Malayalam Unicode block: U+0D00–U+0D7F
_MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")


def detect_language(name: str, phone: str) -> MessageLanguage:
    """
    Heuristic: if the customer name contains Malayalam script characters,
    send the Malayalam template. Otherwise English.

    Phone-number country code (+91 Kerala) is not a reliable signal since
    many Kerala residents use names in Latin script — name is the better proxy.
    """
    if _MALAYALAM_RE.search(name or ""):
        return MessageLanguage.MALAYALAM
    return MessageLanguage.ENGLISH


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

# Message Templates (must match exactly what is submitted to Twilio/Meta for approval)
# Variables: {{1}} = customer_first_name, {{2}} = short_ref
# Media header: image (the artwork PNG)
#
# See docs/whatsapp_template_submission.md for the full submission guide.

TEMPLATES: dict[MessageLanguage, dict] = {
    MessageLanguage.ENGLISH: {
        "sid": None,  # populated from settings at runtime
        "body_preview": (
            "Hi {{1}}! 🎨 Your BOBB design for order {{2}} is ready. "
            "Here's your artwork — show this at the counter when collecting your garment."
        ),
    },
    MessageLanguage.MALAYALAM: {
        "sid": None,
        "body_preview": (
            "നമസ്കാരം {{1}}! 🎨 നിങ്ങളുടെ BOBB ഡിസൈൻ (ഓർഡർ {{2}}) തയ്യാറായി. "
            "ഇതാ നിങ്ങളുടെ ആർട്ട്‌വർക്ക് — വസ്ത്രം ശേഖരിക്കുമ്പോൾ ഇത് കൗണ്ടറിൽ കാണിക്കുക."
        ),
    },
}


def _get_template_sid(lang: MessageLanguage) -> str:
    if lang == MessageLanguage.MALAYALAM:
        sid = settings.twilio_template_sid_ml
    else:
        sid = settings.twilio_template_sid_en

    if not sid:
        raise ValueError(
            f"Twilio template SID for language '{lang}' is not configured. "
            f"Set TWILIO_TEMPLATE_SID_EN / TWILIO_TEMPLATE_SID_ML in environment."
        )
    return sid


# ---------------------------------------------------------------------------
# Phone number normalisation
# ---------------------------------------------------------------------------

def normalise_phone(raw: str) -> str:
    """
    Normalise an Indian mobile number to E.164 format (+91XXXXXXXXXX).
    Accepts:
        9876543210        → +919876543210
        09876543210       → +919876543210
        +919876543210     → +919876543210
        +91-9876-543-210  → +919876543210
    Raises ValueError for numbers that don't look like Indian mobiles.
    """
    digits = re.sub(r"[\s\-\(\)]", "", raw)

    if digits.startswith("+"):
        e164 = digits
    elif digits.startswith("91") and len(digits) == 12:
        e164 = f"+{digits}"
    elif digits.startswith("0") and len(digits) == 11:
        e164 = f"+91{digits[1:]}"
    elif len(digits) == 10:
        e164 = f"+91{digits}"
    else:
        raise ValueError(f"Cannot normalise phone number: {raw!r}")

    # Validate: +91 followed by 10 digits, starting with 6–9
    if not re.fullmatch(r"\+91[6-9]\d{9}", e164):
        raise ValueError(f"Normalised number {e164!r} does not look like a valid Indian mobile")

    return e164


def to_whatsapp_address(phone: str) -> str:
    """Prepend 'whatsapp:' prefix required by Twilio."""
    return f"whatsapp:{normalise_phone(phone)}"


# ---------------------------------------------------------------------------
# Media URL construction
# ---------------------------------------------------------------------------

def build_media_url(image_url: str) -> str:
    """
    Twilio requires a publicly accessible HTTPS URL for media headers.
    If image_url is already an absolute HTTPS URL (e.g. fal.ai CDN), use it directly.
    If it's a relative path, prepend PUBLIC_MEDIA_BASE_URL.
    Raises ValueError if the result is not a valid HTTPS URL.
    """
    if image_url.startswith("https://"):
        return image_url

    if image_url.startswith("http://"):
        raise ValueError(
            f"Twilio requires HTTPS media URLs. Got: {image_url!r}. "
            f"Serve the image over HTTPS or use the fal.ai CDN URL directly."
        )

    # Relative path — prepend base URL
    base = (settings.public_media_base_url or "").rstrip("/")
    if not base:
        raise ValueError(
            "PUBLIC_MEDIA_BASE_URL is not set and image_url is a relative path. "
            "Cannot construct a public media URL for Twilio."
        )
    path = image_url.lstrip("/")
    url = f"{base}/{path}"

    if not url.startswith("https://"):
        raise ValueError(f"Constructed media URL {url!r} is not HTTPS.")

    return url


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------

class WhatsAppDeliveryResult:
    __slots__ = ("success", "message_sid", "error", "phone", "language")

    def __init__(
        self,
        success: bool,
        phone: str,
        language: MessageLanguage,
        message_sid: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success     = success
        self.message_sid = message_sid
        self.error       = error
        self.phone       = phone
        self.language    = language

    def __repr__(self) -> str:
        if self.success:
            return f"<WhatsAppDeliveryResult OK sid={self.message_sid} lang={self.language}>"
        return f"<WhatsAppDeliveryResult FAILED error={self.error!r}>"


async def send_artwork(
    *,
    customer_phone: str,
    customer_name: str,
    short_ref: str,
    image_url: str,
    order_id: str,
) -> WhatsAppDeliveryResult:
    """
    Send the AI artwork PNG to the customer via WhatsApp.

    Called automatically when an order transitions to 'ready'.
    Selects the correct language template based on the customer name.

    Returns a WhatsAppDeliveryResult — never raises. All errors are caught
    and logged so that a Twilio failure never blocks the status transition.
    """
    lang = detect_language(customer_name, customer_phone)

    try:
        to_address  = to_whatsapp_address(customer_phone)
        media_url   = build_media_url(image_url)
        template_sid = _get_template_sid(lang)
        first_name  = (customer_name or "there").split()[0]

        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)

        message = client.messages.create(
            from_=settings.twilio_whatsapp_from,
            to=to_address,
            content_sid=template_sid,
            content_variables=f'{{"1":"{first_name}","2":"{short_ref}"}}',
            media_url=[media_url],
        )

        logger.info(
            "WhatsApp artwork sent",
            extra={
                "order_id":    order_id,
                "short_ref":   short_ref,
                "to":          to_address,
                "sid":         message.sid,
                "language":    lang,
                "media_url":   media_url,
            },
        )

        return WhatsAppDeliveryResult(
            success=True,
            phone=to_address,
            language=lang,
            message_sid=message.sid,
        )

    except ValueError as exc:
        # Config or input validation error — not retryable
        logger.error(
            "WhatsApp send skipped — validation error",
            extra={"order_id": order_id, "error": str(exc)},
        )
        return WhatsAppDeliveryResult(
            success=False,
            phone=customer_phone,
            language=lang,
            error=f"validation_error: {exc}",
        )

    except TwilioRestException as exc:
        logger.error(
            "WhatsApp send failed — Twilio error",
            extra={
                "order_id": order_id,
                "twilio_code": exc.code,
                "twilio_msg":  exc.msg,
                "status":      exc.status,
            },
        )
        return WhatsAppDeliveryResult(
            success=False,
            phone=customer_phone,
            language=lang,
            error=f"twilio_{exc.code}: {exc.msg}",
        )

    except Exception as exc:
        logger.exception(
            "WhatsApp send failed — unexpected error",
            extra={"order_id": order_id, "error": str(exc)},
        )
        return WhatsAppDeliveryResult(
            success=False,
            phone=customer_phone,
            language=lang,
            error=f"unexpected: {exc}",
        )
