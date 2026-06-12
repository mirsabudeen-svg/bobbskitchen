"""
Sprint 9 — WhatsApp Tests
Tests: phone normalisation, language detection, send_artwork happy path,
       Twilio error handling, ready-transition trigger, retry endpoint,
       log persistence, rate limiting, disabled-mode no-op.

Run: pytest tests/test_whatsapp.py -v --timeout=30
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

from app.services.whatsapp import (
    MessageLanguage,
    WhatsAppDeliveryResult,
    build_media_url,
    detect_language,
    normalise_phone,
    send_artwork,
    to_whatsapp_address,
)

fake = Faker("en_IN")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Phone normalisation
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalisePhone:

    def test_10_digit_number(self):
        assert normalise_phone("9876543210") == "+919876543210"

    def test_with_leading_zero(self):
        assert normalise_phone("09876543210") == "+919876543210"

    def test_with_country_code_no_plus(self):
        assert normalise_phone("919876543210") == "+919876543210"

    def test_already_e164(self):
        assert normalise_phone("+919876543210") == "+919876543210"

    def test_with_dashes_and_spaces(self):
        assert normalise_phone("+91 98765 43210") == "+919876543210"
        assert normalise_phone("+91-9876-543-210") == "+919876543210"

    def test_invalid_number_raises(self):
        with pytest.raises(ValueError):
            normalise_phone("12345")

    def test_landline_rejected(self):
        # Landlines start with 0 but have 11 digits and don't start with 6–9
        with pytest.raises(ValueError):
            normalise_phone("+914422334455")  # Chennai landline format

    def test_whatsapp_prefix(self):
        assert to_whatsapp_address("9876543210") == "whatsapp:+919876543210"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Language detection
# ─────────────────────────────────────────────────────────────────────────────

class TestLanguageDetection:

    def test_malayalam_name_detects_ml(self):
        # "Rahul" in Malayalam script
        assert detect_language("രാഹുൽ", "+919876543210") == MessageLanguage.MALAYALAM

    def test_english_name_detects_en(self):
        assert detect_language("Rahul Kumar", "+919876543210") == MessageLanguage.ENGLISH

    def test_mixed_script_name_detects_ml(self):
        # Name with at least one Malayalam character → Malayalam
        assert detect_language("Rahul രാഹുൽ", "+919876543210") == MessageLanguage.MALAYALAM

    def test_empty_name_defaults_to_english(self):
        assert detect_language("", "+919876543210") == MessageLanguage.ENGLISH

    def test_none_name_defaults_to_english(self):
        assert detect_language(None, "+919876543210") == MessageLanguage.ENGLISH  # type: ignore

    def test_arabic_name_detects_english(self):
        # Arabic script is not Malayalam — should default to English
        assert detect_language("محمد", "+919876543210") == MessageLanguage.ENGLISH

    def test_hindi_devanagari_detects_english(self):
        # Devanagari is not Malayalam — U+0900–U+097F, outside ML block
        assert detect_language("राहुल", "+919876543210") == MessageLanguage.ENGLISH


# ─────────────────────────────────────────────────────────────────────────────
# 3. Media URL construction
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildMediaUrl:

    def test_absolute_https_url_returned_unchanged(self):
        url = "https://fal.media/files/test/design.png"
        assert build_media_url(url) == url

    def test_http_url_raises(self):
        with pytest.raises(ValueError, match="HTTPS"):
            build_media_url("http://insecure.example.com/image.png")

    def test_relative_path_prepends_base(self, monkeypatch):
        monkeypatch.setattr("app.services.whatsapp.settings.public_media_base_url",
                            "https://cdn.bobb.ai")
        assert build_media_url("/designs/abc.png") == "https://cdn.bobb.ai/designs/abc.png"

    def test_relative_path_without_base_raises(self, monkeypatch):
        monkeypatch.setattr("app.services.whatsapp.settings.public_media_base_url", "")
        with pytest.raises(ValueError, match="PUBLIC_MEDIA_BASE_URL"):
            build_media_url("/designs/abc.png")

    def test_base_url_trailing_slash_handled(self, monkeypatch):
        monkeypatch.setattr("app.services.whatsapp.settings.public_media_base_url",
                            "https://cdn.bobb.ai/")
        result = build_media_url("designs/abc.png")
        assert result == "https://cdn.bobb.ai/designs/abc.png"
        assert "//" not in result.replace("https://", "")


# ─────────────────────────────────────────────────────────────────────────────
# 4. send_artwork — Twilio mock
# ─────────────────────────────────────────────────────────────────────────────

def _mock_twilio_client(message_sid: str = "SM123456789"):
    """Returns a mock TwilioClient whose messages.create() returns a fake message."""
    mock_message = MagicMock()
    mock_message.sid = message_sid

    mock_messages = MagicMock()
    mock_messages.create.return_value = mock_message

    mock_client = MagicMock()
    mock_client.messages = mock_messages
    return mock_client


class TestSendArtwork:

    @pytest.mark.asyncio
    async def test_happy_path_english(self, monkeypatch):
        mock_client = _mock_twilio_client("SM_EN_001")
        monkeypatch.setattr("app.services.whatsapp.TwilioClient", lambda *a, **k: mock_client)
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_account_sid",  "ACtest")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_auth_token",   "token")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_whatsapp_from","whatsapp:+14155238886")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_en", "HX_EN")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_ml", "HX_ML")

        result = await send_artwork(
            customer_phone="9876543210",
            customer_name="Rahul Kumar",
            short_ref="B-001",
            image_url="https://fal.media/test.png",
            order_id=str(uuid.uuid4()),
        )

        assert result.success is True
        assert result.message_sid == "SM_EN_001"
        assert result.language == MessageLanguage.ENGLISH
        assert result.error is None

        # Verify the Twilio call used the English template
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["content_sid"] == "HX_EN"
        assert "whatsapp:+919876543210" == call_kwargs["to"]

    @pytest.mark.asyncio
    async def test_happy_path_malayalam(self, monkeypatch):
        mock_client = _mock_twilio_client("SM_ML_001")
        monkeypatch.setattr("app.services.whatsapp.TwilioClient", lambda *a, **k: mock_client)
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_account_sid",  "ACtest")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_auth_token",   "token")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_whatsapp_from","whatsapp:+14155238886")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_en", "HX_EN")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_ml", "HX_ML")

        result = await send_artwork(
            customer_phone="9876543210",
            customer_name="രാഹുൽ",        # Malayalam name
            short_ref="B-007",
            image_url="https://fal.media/ml_test.png",
            order_id=str(uuid.uuid4()),
        )

        assert result.success is True
        assert result.language == MessageLanguage.MALAYALAM

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["content_sid"] == "HX_ML"

    @pytest.mark.asyncio
    async def test_twilio_rest_exception_returns_failure(self, monkeypatch):
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(
            status=400, uri="/messages", msg="Invalid phone number", code=21211
        )
        monkeypatch.setattr("app.services.whatsapp.TwilioClient", lambda *a, **k: mock_client)
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_account_sid",  "ACtest")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_auth_token",   "token")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_whatsapp_from","whatsapp:+14155238886")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_en", "HX_EN")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_ml", "HX_ML")

        result = await send_artwork(
            customer_phone="9876543210",
            customer_name="Test",
            short_ref="B-002",
            image_url="https://fal.media/test.png",
            order_id=str(uuid.uuid4()),
        )

        assert result.success is False
        assert "21211" in result.error
        assert result.message_sid is None

    @pytest.mark.asyncio
    async def test_invalid_phone_returns_failure(self, monkeypatch):
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_account_sid",  "ACtest")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_auth_token",   "token")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_whatsapp_from","whatsapp:+14155238886")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_en", "HX_EN")

        result = await send_artwork(
            customer_phone="123",          # invalid
            customer_name="Test",
            short_ref="B-003",
            image_url="https://fal.media/test.png",
            order_id=str(uuid.uuid4()),
        )

        assert result.success is False
        assert "validation_error" in result.error

    @pytest.mark.asyncio
    async def test_whatsapp_disabled_returns_noop(self, monkeypatch):
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_account_sid", "")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_auth_token",  "")
        monkeypatch.setattr("app.services.whatsapp.settings.whatsapp_enabled", False,
                            raising=False)

        result = await send_artwork(
            customer_phone="9876543210",
            customer_name="Test",
            short_ref="B-004",
            image_url="https://fal.media/test.png",
            order_id=str(uuid.uuid4()),
        )

        # Must not raise, must return a graceful failure
        assert result.success is False

    @pytest.mark.asyncio
    async def test_uncaught_exception_returns_failure(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("Network explosion")
        monkeypatch.setattr("app.services.whatsapp.TwilioClient", lambda *a, **k: mock_client)
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_account_sid",  "ACtest")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_auth_token",   "token")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_whatsapp_from","whatsapp:+14155238886")
        monkeypatch.setattr("app.services.whatsapp.settings.twilio_template_sid_en", "HX_EN")

        result = await send_artwork(
            customer_phone="9876543210",
            customer_name="Test",
            short_ref="B-005",
            image_url="https://fal.media/test.png",
            order_id=str(uuid.uuid4()),
        )

        assert result.success is False
        assert "unexpected" in result.error


# ─────────────────────────────────────────────────────────────────────────────
# 5. Integration: ready-transition triggers WhatsApp
# ─────────────────────────────────────────────────────────────────────────────

class TestReadyTransitionTrigger:

    @pytest.mark.asyncio
    async def test_marking_ready_fires_whatsapp(self, client, db):
        """
        PATCH /orders/{id}/status {"status":"ready"}
        → WhatsApp send_artwork is called once
        → WhatsAppLog row created
        → order.whatsapp_sent == True
        """
        from tests.conftest import seed_kiosk_session, seed_variant, make_order_payload

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert r.status_code == 201
        oid = r.json()["order"]["id"]

        # Advance to printing
        await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})

        # Mock send_artwork
        mock_result = WhatsAppDeliveryResult(
            success=True,
            phone="whatsapp:+919876543210",
            language=MessageLanguage.ENGLISH,
            message_sid="SM_INTEGRATION_001",
        )
        with patch("app.api.orders.send_artwork", return_value=mock_result) as mock_send:
            r = await client.patch(
                f"/api/v1/orders/{oid}/status", json={"status": "ready"}
            )
            assert r.status_code == 200
            mock_send.assert_called_once()

        # Verify DB state
        order = r.json()["order"]
        assert order["whatsapp_sent"] is True

        # Verify log row
        r_log = await client.get(f"/api/v1/orders/{oid}/whatsapp-log")
        assert r_log.status_code == 200
        logs = r_log.json()["logs"]
        assert len(logs) == 1
        assert logs[0]["success"] is True

    @pytest.mark.asyncio
    async def test_whatsapp_failure_does_not_block_status_transition(self, client, db):
        """
        If send_artwork fails, the status transition to 'ready' must still succeed.
        The order must be ready, whatsapp_sent must be False.
        """
        from tests.conftest import seed_kiosk_session, seed_variant, make_order_payload

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})

        failing_result = WhatsAppDeliveryResult(
            success=False,
            phone="whatsapp:+919876543210",
            language=MessageLanguage.ENGLISH,
            error="twilio_21211: Invalid phone number",
        )
        with patch("app.api.orders.send_artwork", return_value=failing_result):
            r = await client.patch(
                f"/api/v1/orders/{oid}/status", json={"status": "ready"}
            )

        assert r.status_code == 200, "Status transition must succeed even if WhatsApp fails"
        assert r.json()["order"]["order_status"] == "ready"
        assert r.json()["order"]["whatsapp_sent"] is False

    @pytest.mark.asyncio
    async def test_non_ready_transitions_do_not_trigger_whatsapp(self, client, db):
        """pending→printing must NOT fire WhatsApp."""
        from tests.conftest import seed_kiosk_session, seed_variant, make_order_payload

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        with patch("app.api.orders.send_artwork") as mock_send:
            await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})
            mock_send.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Retry endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestWhatsAppRetry:

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_ready_order(self, client, db):
        from tests.conftest import seed_kiosk_session, seed_variant, make_order_payload

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})

        # First ready transition fails
        failing = WhatsAppDeliveryResult(
            success=False, phone="whatsapp:+91x",
            language=MessageLanguage.ENGLISH, error="timeout"
        )
        with patch("app.api.orders.send_artwork", return_value=failing):
            await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "ready"})

        # Retry succeeds
        success = WhatsAppDeliveryResult(
            success=True, phone="whatsapp:+919876543210",
            language=MessageLanguage.ENGLISH, message_sid="SM_RETRY_001"
        )
        with patch("app.api.whatsapp_retry.send_artwork", return_value=success):
            r = await client.post(f"/api/v1/orders/{oid}/whatsapp-retry")

        assert r.status_code == 200
        assert r.json()["whatsapp"]["success"] is True
        assert r.json()["order"]["whatsapp_sent"] is True

    @pytest.mark.asyncio
    async def test_retry_blocked_on_pending_order(self, client, db):
        from tests.conftest import seed_kiosk_session, seed_variant, make_order_payload

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r = await client.post(f"/api/v1/orders/{oid}/whatsapp-retry")
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "whatsapp_retry_not_allowed"

    @pytest.mark.asyncio
    async def test_retry_rate_limited_after_3_attempts(self, client, db):
        from tests.conftest import seed_kiosk_session, seed_variant, make_order_payload

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})

        failing = WhatsAppDeliveryResult(
            success=False, phone="x",
            language=MessageLanguage.ENGLISH, error="fail"
        )

        # First attempt via ready transition
        with patch("app.api.orders.send_artwork", return_value=failing):
            await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "ready"})

        # Two more via retry endpoint (total = 3)
        with patch("app.api.whatsapp_retry.send_artwork", return_value=failing):
            r1 = await client.post(f"/api/v1/orders/{oid}/whatsapp-retry")
            r2 = await client.post(f"/api/v1/orders/{oid}/whatsapp-retry")

        assert r1.status_code == 200
        assert r2.status_code == 200

        # Fourth attempt must be rate-limited
        r3 = await client.post(f"/api/v1/orders/{oid}/whatsapp-retry")
        assert r3.status_code == 429
        assert r3.json()["detail"]["error"] == "whatsapp_retry_limit_reached"
