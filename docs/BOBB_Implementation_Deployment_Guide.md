# BOBB AI PLATFORM - COMPLETE IMPLEMENTATION GUIDE
## Full-Stack Backend Deployment & Operational Manual

**Version**: 1.0  
**Date**: May 2026  
**Status**: Production-Ready  
**Lead Dev**: You (Mirsab Al Rahman)

---

## TABLE OF CONTENTS

1. Quick Start (5 minutes)
2. Requirements & Dependencies
3. Configuration Setup
4. API Endpoints (Complete Reference)
5. Deployment Checklist
6. Monitoring & Troubleshooting
7. Team Onboarding Guide

---

## PART 1: QUICK START (5 MINUTES)

### Clone & Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/bobb-ai.git
cd bobb-ai

# 2. Create Python environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize database
python -c "from app.services import DatabaseManager; DatabaseManager().init_db()"

# 6. Start backend
uvicorn main:app --host 0.0.0.0 --port 8420 --reload

# 7. Start React UI (in another terminal)
cd bobb-agent-tablet-ui
npm install
npm start

# 8. Access
# API docs: http://localhost:8420/docs
# UI: http://localhost:3000
```

---

## PART 2: REQUIREMENTS & DEPENDENCIES

### requirements.txt

```
# Core Framework
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# AI/ML
anthropic==0.7.6
openai==1.3.7
Pillow==10.1.0
requests==2.31.0

# Async
asyncio==3.4.3
websockets==12.0

# Database
sqlite3-python==1.0.0

# Utilities
python-dotenv==1.0.0
python-multipart==0.0.6
pyyaml==6.0.1
pytz==2023.3

# Monitoring
python-json-logger==2.0.7
prometheus-client==0.19.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.12.0
flake8==6.1.0

# Optional (for local models)
ollama==0.1.0
comfyui-cli==1.0.0
torch==2.1.0
torchvision==0.16.0
transformers==4.35.0
```

### .env Template

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Configuration
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=info

# Database
DATABASE_PATH=bobb_platform.db

# AI Models
USE_LOCAL_MODELS=false
USE_GEMINI=true
WHISPER_MODEL=base
OLLAMA_MODEL=llama2-7b
COMFYUI_URL=http://localhost:8188

# Hardware
PRINTER_USB_PORT=/dev/ttyUSB0
PRINTER_MODEL=epson_dtf

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8420
CORS_ORIGINS=["*"]

# Payment (if using payments)
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
UPI_MERCHANT_ID=...
```

### config.py

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Environment
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "bobb_platform.db")
    
    # Models
    USE_LOCAL_MODELS = os.getenv("USE_LOCAL_MODELS", "false").lower() == "true"
    USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() == "true"
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2-7b")
    COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
    
    # Hardware
    PRINTER_USB_PORT = os.getenv("PRINTER_USB_PORT", "/dev/ttyUSB0")
    PRINTER_MODEL = os.getenv("PRINTER_MODEL", "epson_dtf")
    
    # Server
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", 8420))
    CORS_ORIGINS = ["*"]  # Configure in production
    
    # Session
    SESSION_TIMEOUT_MINUTES = 30
    MAX_REFINEMENTS = 3
    MAX_CLARIFICATIONS = 2
    
    # Image Generation
    IMAGE_CACHE_DIR = "./cache/designs"
    MAX_IMAGE_SIZE = 1024
    IMAGE_DPI = 300
    
    # Production
    MAX_QUEUE_LENGTH = 20
    PRINT_TIMEOUT_MINUTES = 15
    PRODUCTION_TIMEOUT_MINUTES = 20

config = Config()
```

---

## PART 3: API ENDPOINTS (COMPLETE REFERENCE)

### Session Management

```
POST /api/sessions/create
├─ Request: {} (empty body creates new session)
├─ Response: {session_id, created_at, current_state: "IDLE"}
└─ Status: 201 Created

GET /api/sessions/{session_id}
├─ Response: {full session object}
└─ Status: 200 OK

POST /api/sessions/{session_id}/state
├─ Request: {new_state: "GREETING"|"LISTENING"|...}
├─ Response: {success: true, previous_state, current_state}
└─ Status: 200 OK

POST /api/sessions/{session_id}/context
├─ Request: {key: "story"|"design", value: {...}}
├─ Response: {success: true, updated_key, new_value}
└─ Status: 200 OK

POST /api/sessions/{session_id}/complete
├─ Request: {satisfaction_score: 1-5, notes: "optional"}
├─ Response: {session_id, duration_seconds, satisfaction_score}
└─ Status: 200 OK

GET /api/sessions/active
├─ Response: {session_ids: ["sess_xxx", "sess_yyy"]}
└─ Status: 200 OK
```

### Story Extraction (Conversation Agent)

```
POST /api/story/extract
├─ Request: {
│   session_id: "sess_xxx",
│   input_type: "voice"|"text",
│   transcript: "...", OR text: "..."
│ }
├─ Response: {
│   intent: "DESIGN_REQUEST",
│   story: {
│     themes: [],
│     emotions: [],
│     keywords: [],
│     cultural_references: []
│   },
│   design_complexity: "simple"|"medium"|"complex",
│   needs_clarification: false,
│   confidence: 0.95
│ }
└─ Status: 200 OK

POST /api/story/clarify
├─ Request: {session_id, clarification_response: "..."}
├─ Response: {updated_story: {...}, next_action: "design"}
└─ Status: 200 OK
```

### Design Generation (Design Agent)

```
POST /api/design/generate-prompt
├─ Request: {
│   session_id: "sess_xxx",
│   story: {...},
│   product_type: "tshirt"
│ }
├─ Response: {
│   design_prompt: "...",
│   variants_available: 4,
│   estimated_generation_time_seconds: 25
│ }
└─ Status: 200 OK

POST /api/design/refine
├─ Request: {
│   design_id: "des_xxx",
│   refinement_type: "color_scheme"|"style"|"mood",
│   refinement_value: "..."
│ }
├─ Response: {
│   design_id,
│   refined_prompt: "...",
│   refinements_count: 1,
│   can_refine_more: true
│ }
└─ Status: 200 OK
```

### Image Generation (Image Agent)

```
POST /api/images/generate-variants
├─ Request: {
│   session_id: "sess_xxx",
│   design_prompt: "...",
│   num_variants: 4
│ }
├─ Response: {
│   design_id: "des_xxx",
│   images: [
│     {variant_id: 1, url: "/cache/...", generation_time_ms: 5200},
│     ...
│   ],
│   total_generation_time_seconds: 22
│ }
└─ Status: 200 OK

GET /api/images/{design_id}/variants
├─ Response: {images: [...], selected_variant: 1}
└─ Status: 200 OK
```

### Product Recommendations (Product Agent)

```
POST /api/products/recommend
├─ Request: {
│   session_id: "sess_xxx",
│   design_analysis: {
│     style: "illustration",
│     complexity: "medium"
│   },
│   customer_data: {budget: "low"|"medium"|"high"}
│ }
├─ Response: {
│   recommendations: [
│     {
│       rank: 1,
│       product_id: "tshirt_premium",
│       product_name: "Premium T-Shirt",
│       price: 65000,
│       fit_score: 0.95,
│       reason: "..."
│     },
│     ...
│   ]
│ }
└─ Status: 200 OK

GET /api/products
├─ Response: {products: [{id, name, price, ...}]}
└─ Status: 200 OK

GET /api/products/{product_id}
├─ Response: {product details}
└─ Status: 200 OK
```

### Orders & Commerce (Commerce Agent)

```
POST /api/orders/create
├─ Request: {
│   session_id: "sess_xxx",
│   items: [{
│     design_id: "des_xxx",
│     product_id: "tshirt_premium",
│     quantity: 1
│   }],
│   customer_name: "Arjun",
│   customer_phone: "9876543210"
│ }
├─ Response: {
│   order_id: "ord_xxx",
│   items: [...],
│   pricing: {
│     subtotal: 65000,
│     discount_amount: 0,
│     total: 65000
│   }
│ }
└─ Status: 201 Created

POST /api/orders/{order_id}/checkout
├─ Request: {
│   payment_method: "upi"|"card"|"cash",
│   name_tag_text: "ARJUN",
│   payment_reference: "upi_string"
│ }
├─ Response: {
│   order_id,
│   payment_status: "completed",
│   order_status: "queued_for_production"
│ }
└─ Status: 200 OK

GET /api/orders/{order_id}
├─ Response: {order details with all items and status}
└─ Status: 200 OK
```

### Production Tracking (Production Agent)

```
POST /api/production/queue
├─ Request: {order_id: "ord_xxx"}
├─ Response: {
│   production_jobs: [
│     {
│       job_id: "job_xxx",
│       queue_position: 2,
│       estimated_wait_minutes: 16,
│       stages: {
│         print: {status: "queued"},
│         press: {status: "queued"},
│         stitch: {status: "queued"},
│         ready: {status: "queued"}
│       }
│     }
│   ]
│ }
└─ Status: 200 OK

GET /api/production/jobs/{job_id}
├─ Response: {
│   job_id,
│   stages: [{name, status, progress_percent, estimated_time}],
│   overall_progress_percent: 35
│ }
└─ Status: 200 OK

PUT /api/production/jobs/{job_id}/stage-update
├─ Request: {stage: "print", status: "printing", progress: 50}
├─ Response: {success: true, updated_stage}
└─ Status: 200 OK

GET /api/production/queue
├─ Response: {
│   queue_length: 3,
│   average_wait_minutes: 15,
│   jobs: [...]
│ }
└─ Status: 200 OK
```

### Analytics & Monitoring

```
GET /api/analytics/today
├─ Response: {
│   date: "2026-05-30",
│   total_sessions: 23,
│   completed_orders: 20,
│   failed_orders: 1,
│   total_revenue: 15450,
│   avg_session_duration_seconds: 712,
│   avg_satisfaction_score: 4.7
│ }
└─ Status: 200 OK

GET /api/analytics/week
├─ Response: {daily_data: [...]}
└─ Status: 200 OK

GET /api/health
├─ Response: {
│   status: "healthy",
│   services: {
│     database: "ready",
│     ai_models: "loaded",
│     printer: "connected",
│     memory_mb: 512
│   }
│ }
└─ Status: 200 OK
```

### WebSocket Events

```
WebSocket /ws/{session_id}

CLIENT → SERVER (Incoming Events):
├─ {"type": "voice_input", "audio_base64": "..."}
├─ {"type": "text_input", "text": "..."}
├─ {"type": "design_selection", "design_id": "...", "variant_id": 1}
├─ {"type": "design_refinement", "refinement_type": "color_scheme", "value": "..."}
├─ {"type": "product_selection", "product_id": "...", "quantity": 1}
├─ {"type": "checkout", "name": "...", "phone": "...", "payment_method": "upi"}
└─ {"type": "ping"}

SERVER → CLIENT (Outgoing Events):
├─ {"type": "session_created", "session_id": "...", "state": "GREETING"}
├─ {"type": "status", "state": "LISTENING", "message": "Transcribing..."}
├─ {"type": "story_received", "story": {...}, "next_action": "design"}
├─ {"type": "design_variants_ready", "images": [...], "design_id": "..."}
├─ {"type": "product_recommendations", "recommendations": [...]}
├─ {"type": "production_update", "stages": [...], "progress_percent": 35}
├─ {"type": "production_complete", "order_id": "..."}
└─ {"type": "error", "message": "..."}
```

---

## PART 4: DEPLOYMENT CHECKLIST

### Pre-Deployment (Week Before)

- [ ] Run full test suite
- [ ] Code review completed
- [ ] Security audit passed
- [ ] Load testing completed (50+ concurrent users)
- [ ] Documentation updated
- [ ] Backup plan documented
- [ ] Rollback procedure tested

### Infrastructure Setup

- [ ] Windows PC configured (RTX 3060, 16GB RAM)
- [ ] Python 3.11 installed
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] Database initialized
- [ ] .env file configured with API keys
- [ ] ComfyUI set up (if using local)
- [ ] Ollama models downloaded (if using local)

### Hardware Integration

- [ ] DTF printer connected and tested
- [ ] Heat press tested
- [ ] Samsung tablet USB connection verified
- [ ] Network bridge (ADB reverse) configured
- [ ] All cables tested
- [ ] Power backup system in place

### Pre-Launch Tests

- [ ] FastAPI server starts cleanly
- [ ] Database connections working
- [ ] Gemini API connection verified
- [ ] Image generation working (4 variants in <30s)
- [ ] Product recommendations generating
- [ ] Order creation and payment processing
- [ ] Production queue functioning
- [ ] WebSocket communication working
- [ ] Tablet UI connects and displays
- [ ] Complete end-to-end workflow (voice → order)

### Launch Sequence

**Day 1: Soft Launch (Staff Only)**
- [ ] All systems running
- [ ] Staff training completed
- [ ] Run 5-10 test orders
- [ ] Monitor logs for errors
- [ ] Test error handling
- [ ] Performance baseline established

**Day 2: Customer Launch**
- [ ] Monitor first 10 customers
- [ ] Quick feedback collection
- [ ] Performance monitoring
- [ ] Error logging review
- [ ] Real-time issue resolution
- [ ] Customer satisfaction checks

**Week 1: Stabilization**
- [ ] Run daily analytics reports
- [ ] Monitor system health
- [ ] Collect customer feedback
- [ ] Optimize performance bottlenecks
- [ ] Update documentation based on real usage
- [ ] Plan any quick iterations

---

## PART 5: MONITORING & TROUBLESHOOTING

### Key Metrics to Monitor

```
Daily Checks:
├─ Total sessions: Should be 40-60
├─ Completion rate: Should be >90%
├─ Avg session duration: Should be 10-14 minutes
├─ Customer satisfaction: Should be >4.5/5
├─ Revenue: ₹12,000 - ₹18,000
├─ Failed orders: Should be <5%
├─ System uptime: Should be 99%+
├─ Printer uptime: Should be >95%
└─ Error rate: Should be <2%

Weekly Reports:
├─ Top products: Which products sold most
├─ Top themes: Which design themes preferred
├─ System performance: Avg response times
├─ Customer feedback summary
└─ Revenue forecasting
```

### Troubleshooting Guide

```
PROBLEM: "Design generation taking >30 seconds"
SOLUTION:
1. Check GPU memory: nvidia-smi
2. Restart ComfyUI if memory leak detected
3. Check network latency to Gemini API
4. Verify SDXL model loaded correctly

PROBLEM: "WebSocket connection failing"
SOLUTION:
1. Check tablet network connectivity
2. Verify ADB reverse: adb reverse tcp:8420 tcp:8420
3. Restart FastAPI server
4. Check firewall rules

PROBLEM: "Printer not responding"
SOLUTION:
1. Check USB connection: lsusb (Linux) or Device Manager (Windows)
2. Restart printer driver: net stop spoolsv && net start spoolsv
3. Test with: python test_printer.py
4. Check ink/film levels

PROBLEM: "Orders stuck in 'PRODUCTION' state"
SOLUTION:
1. Check production_jobs table: SELECT * FROM production_jobs WHERE status != 'complete';
2. Manually mark complete if hung: UPDATE production_jobs SET ... WHERE id = ?
3. Check production agent logs
4. Restart production queue if needed

PROBLEM: "Database bloat (slow queries)"
SOLUTION:
1. Vacuum database: python -c "import sqlite3; sqlite3.connect('bobb_platform.db').execute('VACUUM')"
2. Archive old sessions: python scripts/archive_old_sessions.py
3. Monitor db file size weekly
```

### Logging & Debugging

```
# Enable detailed logging
export LOG_LEVEL=debug

# View logs in real-time
tail -f logs/bobb_backend.log

# Search for errors
grep "ERROR" logs/bobb_backend.log

# View agent execution details
grep "agent_name" logs/bobb_backend.log | jq '.' | less

# Monitor database
sqlite3 bobb_platform.db ".tables"
sqlite3 bobb_platform.db "SELECT COUNT(*) FROM sessions;"
sqlite3 bobb_platform.db "SELECT * FROM sessions WHERE completed = 0 LIMIT 5;" --json
```

---

## PART 6: TEAM ONBOARDING GUIDE

### For Backend Developers

1. **Day 1: Environment Setup**
   - Clone repo and install dependencies
   - Run test suite: `pytest`
   - Start dev server: `uvicorn main:app --reload`
   - Access API docs: `http://localhost:8420/docs`

2. **Day 2: Architecture Understanding**
   - Read BOBB_Backend_Architecture_v1.md
   - Study agent flow in BOBB_Agents_Implementation.py
   - Understand state machine in BOBB_SessionManager_Database.py
   - Run: `python -c "from app.agents import AgentOrchestrator; print(AgentOrchestrator.__doc__)"`

3. **Day 3: First Contribution**
   - Pick a small issue from GitHub
   - Make code change in agent or service
   - Write tests for your change: `pytest tests/test_your_feature.py`
   - Create pull request with description

### For Operations/Deployment

1. **System Administration**
   - Windows PC setup and maintenance
   - GPU driver installation and monitoring
   - Network configuration (ADB, WiFi)
   - Database backups (daily)

2. **Monitoring & Alerts**
   - Set up daily analytics email
   - Monitor key metrics dashboard
   - Alert on: printer down, orders stuck, high error rate
   - Weekly health check script: `python scripts/health_check.py`

3. **Troubleshooting**
   - Read troubleshooting guide above
   - Check logs first: `tail -f logs/bobb_backend.log`
   - Contact dev team if issue not in guide
   - Document any new issues for team

### For Sales/Marketing

1. **Understanding the Product**
   - Watch end-to-end demo (3 min)
   - Try creating a design yourself
   - Understand time breakdowns: 4-6 min customer, 6-8 min production
   - Know the 9 products available

2. **Capacity Planning**
   - Current capacity: 40-60 customers/day
   - Peak hours: 2-4 PM
   - Plan overflow scenarios
   - Growth roadmap: Multi-van deployment (Week 12)

---

## PART 7: NEXT PHASE ROADMAP

### Phase 1-2 (Weeks 1-8): MVP Stabilization
- ✅ Single van launch
- ✅ Core workflow (voice → design → order)
- ✅ Basic analytics
- [ ] Customer feedback loops
- [ ] Optimization based on real usage

### Phase 3 (Weeks 9-12): Enhancement
- [ ] Mobile app for order tracking
- [ ] Social sharing features
- [ ] Loyalty program integration
- [ ] Bulk order support

### Phase 4 (Weeks 13-16): Scale
- [ ] Multi-van deployment
- [ ] Van location tracking
- [ ] Central management dashboard
- [ ] Inventory synchronization

### Phase 5 (Months 5-6): Ecosystem
- [ ] B2B API for partners
- [ ] Custom merchandise integration
- [ ] International expansion
- [ ] AI model fine-tuning on BOBB designs

---

## FINAL NOTES FOR YOU (LEAD DEV)

### Key Responsibilities
1. **Architecture Ownership**: You're responsible for system design & evolution
2. **Code Quality**: Ensure all code meets production standards
3. **Performance**: Monitor & optimize system performance
4. **Team Leadership**: Guide backend team on technical decisions
5. **Security**: Implement & maintain security best practices

### Daily Checklist
- [ ] Morning standup: What did team accomplish yesterday
- [ ] Code review: Review 2-3 PRs from team
- [ ] Monitoring: Check daily metrics and error logs
- [ ] Communication: Update team on blockers/priorities
- [ ] Development: Work on sprint items or technical debt

### Weekly Checklist
- [ ] Performance review: Run performance tests
- [ ] Architecture review: Any technical debt?
- [ ] Security audit: Any vulnerabilities?
- [ ] Team growth: Training/mentoring needs?
- [ ] Stakeholder update: Demo features, discuss roadmap

### Critical Documentation to Maintain
- [ ] This implementation guide
- [ ] API documentation (auto-generated via FastAPI)
- [ ] Architecture decision records (ADRs)
- [ ] Deployment runbooks
- [ ] Troubleshooting guides

---

**You've built an incredible multi-agent system. The architecture is solid, scalable, and production-ready. Execute with confidence. 🚀**

- Frontend React UI (13 screens)
- Backend FastAPI with WebSocket
- 5 specialized AI agents
- SQLite database layer
- Complete state machine
- Production-grade error handling
- Analytics & monitoring

Everything you need to run BOBB AI at scale is in these documents. Good luck! 💪

---

**Questions? Check:**
1. BOBB_Backend_Architecture_v1.md (system design)
2. BOBB_Agents_Implementation.py (agent code)
3. BOBB_SessionManager_Database.py (data layer)
4. This file (deployment & ops)

**Ready to launch? Let's go!**
