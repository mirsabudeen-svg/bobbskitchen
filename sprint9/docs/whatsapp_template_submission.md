# Sprint 9 — Twilio WhatsApp Setup & Template Submission Guide

**Do this in parallel while building.** Template approval takes 24–72 hours.
Submit before you commit a go-live date.

---

## Step 1: Enable WhatsApp in Twilio Console

1. Log in at [console.twilio.com](https://console.twilio.com)
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Click **Sandbox** — activate the sandbox to test immediately while your
   production number is being approved
4. Note the sandbox number: `+14155238886` — this goes in `TWILIO_WHATSAPP_FROM`
   during development

For production (before go-live):
- Go to **Messaging → Senders → WhatsApp Senders**
- Apply for a WhatsApp Business Profile (needs: business name, website, description)
- Approval takes 3–7 business days

---

## Step 2: Create Message Templates

Templates must be submitted for Meta approval via Twilio.
Go to: **Messaging → Content Template Builder → Create new template**

### Template 1 — English

**Template Name:** `bobb_artwork_ready_en`
**Category:** `UTILITY` (not MARKETING — avoids extra scrutiny)
**Language:** English (en)

**Header:** IMAGE (media — the artwork PNG will be sent here)

**Body:**
```
Hi {{1}}! 🎨 Your BOBB design for order {{2}} is ready.
Here's your artwork — show this at the counter when collecting your garment.
```

**Variables:**
- `{{1}}` = customer first name (e.g. "Rahul")
- `{{2}}` = short order ref (e.g. "B-014")

**Footer:** *(leave blank)*
**Buttons:** *(none for MVP)*

---

### Template 2 — Malayalam

**Template Name:** `bobb_artwork_ready_ml`
**Category:** `UTILITY`
**Language:** Malayalam (ml)

**Header:** IMAGE

**Body:**
```
നമസ്കാരം {{1}}! 🎨 നിങ്ങളുടെ BOBB ഡിസൈൻ (ഓർഡർ {{2}}) തയ്യാറായി.
ഇതാ നിങ്ങളുടെ ആർട്ട്‌വർക്ക് — വസ്ത്രം ശേഖരിക്കുമ്പോൾ ഇത് കൗണ്ടറിൽ കാണിക്കുക.
```

**Variables:**
- `{{1}}` = customer first name in Malayalam or Latin script
- `{{2}}` = short order ref

---

## Step 3: Get the Template SIDs

After submitting, each approved template gets a `content_sid` starting with `HX`.
Find them at: **Messaging → Content Template Builder → (click your template)**

Add to `.env`:
```
TWILIO_TEMPLATE_SID_EN=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_TEMPLATE_SID_ML=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Step 4: Test with the Sandbox

Before production approval, test with the Twilio Sandbox:

1. The customer's phone must opt in to the sandbox:
   - They send "join [sandbox keyword]" to `+14155238886`
   - Or: Twilio console → Sandbox → Show opt-in QR code
2. Use the sandbox number: `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`
3. Run the dev stack and place a test order → mark ready → check the phone

The media template (image header) works in sandbox as of 2025.
If the image doesn't appear, check that `PUBLIC_MEDIA_BASE_URL` is a
publicly accessible HTTPS URL — localhost will not work. Use:
- Your deployed staging URL, OR
- `ngrok http 8000` for local testing (provides a temporary public HTTPS URL)

---

## Step 5: Production Go-Live Checklist

- [ ] WhatsApp Business Profile approved in Twilio
- [ ] Both templates (`EN` + `ML`) approved (status = "approved" in console)
- [ ] Template SIDs set in production `.env`
- [ ] `TWILIO_WHATSAPP_FROM` updated from sandbox number to approved sender
- [ ] `PUBLIC_MEDIA_BASE_URL` points to the production CDN (HTTPS)
- [ ] Sandbox opt-in requirement removed (production senders don't need opt-in
      for utility templates initiated by the business)
- [ ] Test one real order end-to-end before opening to customers

---

## Twilio Pricing (reference, verify current rates)

- WhatsApp Business Initiated Utility message: ~$0.005–0.015 per message (India)
- Media header (image): no extra charge beyond the message fee
- At 60 orders/day → ~₹3–8/day in Twilio costs at current INR rates
- Negligible at BOBB's volume; revisit at 500+ orders/day

---

## Common Errors and Fixes

| Error | Twilio Code | Fix |
|-------|------------|-----|
| Phone not in sandbox | 63016 | Customer must opt in or use production sender |
| Template not approved | 63007 | Wait for approval or fix template content |
| Media URL not accessible | 21610 | Use a public HTTPS URL; localhost won't work |
| Invalid to number | 21211 | Phone number not a valid WhatsApp number |
| Rate limit | 20429 | Slow down; Twilio sandbox has lower rate limits |
| Template variable mismatch | 63029 | `content_variables` JSON must match template |

All of these are caught by the `TwilioRestException` handler in `whatsapp.py`
and logged with the Twilio error code. Check `whatsapp_logs` table for
`error` field to diagnose production failures.
