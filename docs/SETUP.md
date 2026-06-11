# BOBB Kitchen — Agent System Setup Guide

## Files

```
bobb_agents.py     ← 10 product agents + orchestrator (core system)
bobb_server.py     ← FastAPI + WebSocket server (connects tablet UI)
requirements.txt   ← Python dependencies
```

---

## Step 1 — Install Ollama (local AI, zero cost)

```bash
# Windows: download from https://ollama.com/download
# Then pull the model:
ollama pull llama3

# Verify it's running:
ollama run llama3
# Type "hello" → you should see a response
# Press Ctrl+D to exit
```

---

## Step 2 — Python environment

```bash
python -m venv bobb_env
bobb_env\Scripts\activate        # Windows
# source bobb_env/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

---

## Step 3 — Test agents in CLI (no server needed)

```bash
python bobb_agents.py
```

This runs an interactive CLI session:
```
═══════════════════════════════════════════════════
  BOBB KITCHEN — Agent CLI Test
  Model: llama3
═══════════════════════════════════════════════════

Session created: TEST-AB12CD

You: I want a t-shirt
BOBB Kitchen: Hi Arjun! Let's create your t-shirt.
              Tell me your story — what do you want to express?

You: I'm from Kannur, now living in Bangalore...
TShirt Design Agent: Beautiful — I'm thinking Backwater Heritage...
```

---

## Step 4 — Switch to Cloud (dev/testing only)

In `bobb_agents.py`, line near top:

```python
# For local production (zero cost):
ACTIVE_MODEL = LOCAL_MODEL        # ← default

# For development with GPT-4o:
ACTIVE_MODEL = CLOUD_MODEL        # ← switch here

# And set your API key:
OPENAI_CLIENT = AsyncOpenAI(api_key="sk-your-key-here")
```

---

## Step 5 — Run the full server

```bash
python bobb_server.py
# Server starts at http://localhost:8420
```

Test endpoints:
```bash
# Health check
curl http://localhost:8420/health

# Create a session (WhatsApp bot does this)
curl -X POST http://localhost:8420/session/create \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"Arjun","phone_number":"+919876543210","language":"en"}'
```

---

## Step 6 — Connect React tablet UI

In your React app (`bobb-agent-tablet-ui.jsx`), connect to WebSocket:

```javascript
const ws = new WebSocket(`ws://localhost:8420/ws/${sessionId}`);

ws.onopen = () => {
  // Greeting arrives automatically — no need to send anything
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === "response") {
    // Show agent text to customer
    setAgentMessage(msg.text);
    setCurrentAgent(msg.agent);
  }

  if (msg.type === "thinking") {
    // Show loading animation
    setIsThinking(true);
  }

  if (msg.type === "payment_confirmed") {
    // Show success screen
    showOrderConfirmation(msg.order_id, msg.eta_mins);
  }
};

// Send customer message
const sendMessage = (text) => {
  ws.send(JSON.stringify({ type: "message", text }));
};

// Customer selected image option 2 (index 1)
const selectImage = (productType, imageIndex) => {
  ws.send(JSON.stringify({
    type: "select_image",
    product_type: productType,
    image_index: imageIndex,
  }));
};

// Customer approved mockup
const approveDesign = (productType) => {
  ws.send(JSON.stringify({
    type: "approve_design",
    product_type: productType,
  }));
};
```

---

## Step 7 — ADB port forwarding (Samsung Tab → PC)

```bash
# Run this on Windows PC whenever tablet is connected:
adb reverse tcp:8420 tcp:8420

# Tablet React app can now reach:
# ws://localhost:8420/ws/{sessionId}
```

---

## Architecture summary

```
Samsung Tab S9 Ultra (React UI)
       ↕ WebSocket  ws://localhost:8420/ws/{session_id}
       ↕ ADB port forward
Windows PC (localhost:8420)
  └── bobb_server.py (FastAPI)
        └── bobb_agents.py
              ├── Orchestrator Agent (Ollama/llama3)
              ├── TShirt Agent      (Ollama/llama3)
              ├── Keychain Agent    (Ollama/llama3)
              ├── ... 8 more agents
              ├── generate_image()  → ComfyUI :8188
              ├── send_to_printer() → Print API :8421
              └── SQLite            bobb_kitchen.db

WhatsApp Bot (Twilio)
  ├── POST /session/create → creates session + QR
  ├── POST /order/{id}/ready → sends pickup notification
  └── Receives payment webhooks → POST /payment/webhook
```

---

## Model comparison (choose per environment)

| | Ollama / Llama3 | GPT-4o |
|---|---|---|
| Cost per session | ₹0 | ~₹150 |
| Works offline | ✅ | ❌ |
| Malayalam quality | Good | Excellent |
| Response speed | Fast (local GPU) | 1-3s API latency |
| Use case | Production store | Development / QA |

---

## Troubleshooting

**Ollama not responding:**
```bash
ollama serve         # start the Ollama server
ollama list          # check llama3 is downloaded
ollama run llama3    # test it directly
```

**Agent not using correct language:**
- Session `language` field controls this
- Pass `language: "ml"` in `/session/create` for Malayalam

**Images not generating:**
- Check ComfyUI is running: `http://localhost:8188`
- Agent falls back to template library automatically

**WebSocket drops:**
- ADB connection may have reset; run `adb reverse tcp:8420 tcp:8420` again
- Server auto-cleans up disconnected sessions
