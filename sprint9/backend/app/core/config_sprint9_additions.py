"""
backend/app/core/config_sprint9_additions.py

Additions to your existing Settings class (app/core/config.py).
Merge these fields into the existing Pydantic BaseSettings model.
"""

# Add these fields to your existing Settings(BaseSettings) class:
#
# class Settings(BaseSettings):
#     ...existing fields...
#
#     # ── Sprint 9: Twilio WhatsApp ─────────────────────────────────────────
#     twilio_account_sid:      str = ""
#     twilio_auth_token:       str = ""
#     twilio_whatsapp_from:    str = "whatsapp:+14155238886"  # Twilio sandbox default
#     twilio_template_sid_en:  str = ""   # approved EN template SID
#     twilio_template_sid_ml:  str = ""   # approved ML template SID
#     public_media_base_url:   str = ""   # e.g. https://cdn.bobb.ai
#
#     @property
#     def whatsapp_enabled(self) -> bool:
#         """True only when all required Twilio credentials are present."""
#         return bool(
#             self.twilio_account_sid
#             and self.twilio_auth_token
#             and self.twilio_whatsapp_from
#             and (self.twilio_template_sid_en or self.twilio_template_sid_ml)
#         )

# ── .env additions ────────────────────────────────────────────────────────────
ENV_TEMPLATE = """
# Sprint 9 — Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_TEMPLATE_SID_EN=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_TEMPLATE_SID_ML=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PUBLIC_MEDIA_BASE_URL=https://cdn.bobb.ai
"""

# ── whatsapp_enabled guard in send_artwork ────────────────────────────────────
# In whatsapp.py, wrap the Twilio call with a settings guard so that
# WhatsApp silently no-ops in environments where credentials aren't set
# (local dev without a Twilio account, test runner with mocked client):
#
# async def send_artwork(...) -> WhatsAppDeliveryResult:
#     if not settings.whatsapp_enabled:
#         logger.info("WhatsApp disabled — skipping send for order %s", order_id)
#         return WhatsAppDeliveryResult(
#             success=False,
#             phone=customer_phone,
#             language=detect_language(customer_name, customer_phone),
#             error="whatsapp_disabled",
#         )
#     ... rest of the function unchanged ...
