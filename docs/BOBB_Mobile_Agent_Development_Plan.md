# BOBB Mobile Van AI Agent — Complete Development Plan
## Optimized for Cursor AI Development

**Version**: 1.0  
**Target Platform**: Mobile Van (Samsung Tab S Ultra → Windows PC)  
**Development Tool**: Cursor AI  
**Timeline**: 8 weeks (2 months)  
**Status**: Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Development Phases](#development-phases)
5. [Cursor AI Workflow](#cursor-ai-workflow)
6. [Component Specifications](#component-specifications)
7. [Deployment Strategy](#deployment-strategy)
8. [Testing & Quality Assurance](#testing--quality-assurance)
9. [Appendices](#appendices)

---

## Executive Summary

### Project Overview

**BOBB Mobile Agent** is an offline-first AI storytelling system deployed in a mobile van. Customers interact with tablets to share stories, which are transformed into custom artwork and printed on merchandise in real-time.

### Key Differentiators

- **Fully Offline**: All AI inference runs locally (no internet required)
- **Mobile Optimized**: Designed for van environment (power, vibration, temperature)
- **Fast Generation**: <30 seconds from story to artwork
- **Production-Ready**: Built for daily commercial operation

### Success Criteria

✅ **Technical**
- Story → artwork: <30 seconds
- System startup: <90 seconds
- 10-minute continuous operation
- 99% uptime during operating hours

✅ **Operational**
- 40-60 customers/day capacity
- 2-person operation
- Simple maintenance protocol
- Robust error recovery

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CUSTOMER LAYER                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │   Tablet UI #1   │         │   Tablet UI #2   │         │
│  │  React + WebSocket│        │  React + WebSocket│        │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                             │                    │
│           └──────────────┬──────────────┘                    │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │ USB-C / ADB Port Forwarding
                           │ tcp:8420
┌──────────────────────────┼───────────────────────────────────┐
│  INFERENCE LAYER (Windows PC)                                │
│                          ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  FastAPI Backend (Python)                              │ │
│  │  - WebSocket server (port 8420)                        │ │
│  │  - Session state machine                               │ │
│  │  - Audio processing pipeline                           │ │
│  └────┬──────────┬──────────┬──────────┬──────────────┬──┘ │
│       │          │          │          │              │     │
│  ┌────▼────┐┌───▼────┐┌────▼────┐┌───▼──────┐┌──────▼───┐ │
│  │ Whisper ││Ollama  ││ComfyUI  ││  SQLite  ││  Print   │ │
│  │  STT    ││Llama3  ││ SDXL    ││  Logger  ││Controller│ │
│  │ (local) ││(local) ││ (local) ││          ││          │ │
│  └─────────┘└────────┘└─────────┘└──────────┘└──────────┘ │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  PRINT LAYER                                                  │
│  DTF Printer → Heat Press → Product Delivery                 │
└──────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. Tablet UI (Frontend)
- **Framework**: React 18 with Vite
- **State Management**: Zustand
- **Communication**: WebSocket (reconnect logic built-in)
- **Audio**: Web Audio API for waveform visualization
- **Styling**: Tailwind CSS + custom BOBB theme

#### 2. Backend API (Python/FastAPI)
- **Framework**: FastAPI + WebSocket support
- **Session Management**: State machine pattern
- **Audio Processing**: Whisper for STT
- **Prompt Generation**: Ollama + Llama3
- **Image Generation**: ComfyUI + SDXL
- **Logging**: SQLite with session tracking
- **Print Control**: Windows print API integration

#### 3. AI Stack (Local Inference)
- **Speech-to-Text**: Whisper (base or small model)
- **Story → Prompt**: Llama3 8B via Ollama
- **Prompt → Image**: SDXL 1.0 via ComfyUI
- **Hardware**: RTX 3060 (12GB VRAM)

---

## Technology Stack

### Core Stack

```yaml
Frontend:
  - React: ^18.2.0
  - Vite: ^5.0.0
  - TypeScript: ^5.3.0
  - Tailwind CSS: ^3.4.0
  - Zustand: ^4.5.0
  - Framer Motion: ^11.0.0

Backend:
  - Python: 3.11
  - FastAPI: ^0.109.0
  - Uvicorn: ^0.27.0
  - WebSockets: built-in
  - Pydantic: ^2.5.0
  - SQLite: built-in

AI Stack:
  - Whisper: openai/whisper (local)
  - Ollama: ^0.1.0 (Llama3 8B)
  - ComfyUI: latest stable
  - SDXL 1.0: stabilityai model

System:
  - OS: Windows 11
  - Node.js: 20.x LTS
  - Python: 3.11
  - CUDA: 12.1+
```

### Hardware Requirements

**Windows PC (In-Van Server)**:
- GPU: RTX 3060 12GB (or better)
- CPU: Intel i5-12400F or AMD Ryzen 5 5600X
- RAM: 32GB DDR4
- Storage: 1TB NVMe SSD
- Power: UPS + van power system

**Tablets (Customer Interface)**:
- Model: Samsung Galaxy Tab S9 Ultra
- Display: 14.6" AMOLED
- RAM: 12GB
- Storage: 256GB
- Connection: USB-C to PC

---

## Development Phases

### Phase 0: Foundation Setup (Week 1)

**Goal**: Environment preparation and tooling setup

**Tasks**:
1. Install development environment
2. Configure Cursor AI workspace
3. Setup project structure
4. Install AI models locally
5. Test hardware connectivity

**Deliverables**:
- ✅ PC with all dependencies installed
- ✅ Ollama running Llama3 locally
- ✅ ComfyUI installed and tested
- ✅ Whisper model downloaded
- ✅ ADB connection tablet ↔ PC verified

**Cursor AI Prompts** (see Section 5)

---

### Phase 1: Backend Core (Week 2)

**Goal**: Build FastAPI backend with WebSocket support

**Components**:
1. FastAPI server setup
2. WebSocket connection handler
3. Session state machine
4. Audio file handling
5. Health monitoring endpoint

**File Structure**:
```
backend/
├── main.py                 # FastAPI app entry
├── config.py               # Configuration
├── session.py              # Session state machine
├── audio_processor.py      # Audio → transcript
├── prompt_generator.py     # Story → prompt
├── image_generator.py      # Prompt → image
├── print_controller.py     # Image → printer
├── database.py             # SQLite logger
├── models/
│   ├── session_model.py
│   └── message_model.py
└── utils/
    ├── logger.py
    └── health_monitor.py
```

**Key Files to Create**:

**`main.py`** (FastAPI + WebSocket):
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from session import SessionManager
from config import Config

app = FastAPI(title="BOBB Agent API")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager()

@app.websocket("/ws/{tablet_id}")
async def websocket_endpoint(websocket: WebSocket, tablet_id: str):
    await session_manager.handle_connection(websocket, tablet_id)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": await check_services()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8420)
```

**Cursor Prompts for Phase 1** (see Section 5)

---

### Phase 2: AI Pipeline (Week 3)

**Goal**: Integrate all AI components into working pipeline

**Components**:
1. Whisper STT integration
2. Ollama + Llama3 prompt generation
3. ComfyUI workflow automation
4. Pipeline orchestration
5. Error handling & retries

**Key Files**:

**`audio_processor.py`** (Whisper Integration):
```python
import whisper
from pathlib import Path
from typing import Optional

class AudioProcessor:
    def __init__(self, model_size: str = "base"):
        self.model = whisper.load_model(model_size)
    
    async def transcribe(self, audio_path: Path) -> dict:
        """Transcribe audio file to text"""
        result = self.model.transcribe(
            str(audio_path),
            language="en",
            fp16=True  # Use half precision on GPU
        )
        return {
            "text": result["text"],
            "confidence": self._calculate_confidence(result),
            "duration": result.get("duration", 0)
        }
```

**`prompt_generator.py`** (Ollama + Llama3):
```python
import ollama
from typing import Dict

class PromptGenerator:
    def __init__(self):
        self.model = "llama3:8b"
        self.system_prompt = self._load_system_prompt()
    
    async def generate_prompt(self, story: str) -> Dict[str, str]:
        """Convert story to SDXL prompt"""
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Story: {story}"}
            ]
        )
        
        return self._parse_response(response)
```

**`image_generator.py`** (ComfyUI Integration):
```python
import requests
import json
from pathlib import Path

class ImageGenerator:
    def __init__(self, comfy_url: str = "http://127.0.0.1:8188"):
        self.base_url = comfy_url
        self.workflow_path = Path("workflows/bobb_sdxl.json")
    
    async def generate(self, prompt: str, negative: str = "") -> Path:
        """Generate image using ComfyUI workflow"""
        workflow = self._load_workflow()
        workflow = self._inject_prompts(workflow, prompt, negative)
        
        # Queue workflow
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow}
        )
        
        prompt_id = response.json()["prompt_id"]
        
        # Poll for completion
        return await self._wait_for_completion(prompt_id)
```

**Cursor Prompts for Phase 2** (see Section 5)

---

### Phase 3: Frontend UI (Week 4)

**Goal**: Build React tablet interface with BOBB brand styling

**Components**:
1. 11-screen state machine
2. WebSocket connection manager
3. Audio recording & waveform
4. Countdown timer
5. Generation progress indicator
6. Print success animation

**Screen Flow**:
```
IDLE → WELCOME → LISTENING → THINKING → 
GENERATING → PREVIEW → PRINTING → SUCCESS → 
ERROR → RESET → IDLE
```

**File Structure**:
```
frontend/
├── src/
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # Entry point
│   ├── components/
│   │   ├── Screen.tsx             # Base screen component
│   │   ├── screens/
│   │   │   ├── IdleScreen.tsx
│   │   │   ├── WelcomeScreen.tsx
│   │   │   ├── ListeningScreen.tsx
│   │   │   ├── ThinkingScreen.tsx
│   │   │   ├── GeneratingScreen.tsx
│   │   │   ├── PreviewScreen.tsx
│   │   │   ├── PrintingScreen.tsx
│   │   │   ├── SuccessScreen.tsx
│   │   │   └── ErrorScreen.tsx
│   │   ├── Waveform.tsx           # Audio visualizer
│   │   ├── Timer.tsx              # Countdown
│   │   └── ProgressBar.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts        # WS connection
│   │   ├── useAudioRecorder.ts    # Recording
│   │   └── useSessionState.ts     # State management
│   ├── store/
│   │   └── sessionStore.ts        # Zustand store
│   ├── styles/
│   │   └── theme.ts               # BOBB theme tokens
│   └── utils/
│       ├── audio.ts
│       └── constants.ts
├── public/
│   └── assets/
│       ├── logo.svg
│       └── animations/
└── vite.config.ts
```

**Key Component: State Machine**

**`App.tsx`** (Main State Machine):
```tsx
import { useEffect } from 'react';
import { useSessionStore } from './store/sessionStore';
import { useWebSocket } from './hooks/useWebSocket';

// Import all screens
import IdleScreen from './components/screens/IdleScreen';
import WelcomeScreen from './components/screens/WelcomeScreen';
import ListeningScreen from './components/screens/ListeningScreen';
// ... other screens

const SCREENS = {
  idle: IdleScreen,
  welcome: WelcomeScreen,
  listening: ListeningScreen,
  thinking: ThinkingScreen,
  generating: GeneratingScreen,
  preview: PreviewScreen,
  printing: PrintingScreen,
  success: SuccessScreen,
  error: ErrorScreen,
};

function App() {
  const { currentScreen, sessionData } = useSessionStore();
  const { connect, disconnect, sendMessage } = useWebSocket();

  useEffect(() => {
    connect('ws://localhost:8420/ws/tablet-1');
    return () => disconnect();
  }, []);

  const CurrentScreen = SCREENS[currentScreen];

  return (
    <div className="app-container">
      <CurrentScreen {...sessionData} />
    </div>
  );
}

export default App;
```

**BOBB Theme Tokens**:

**`styles/theme.ts`**:
```typescript
export const theme = {
  colors: {
    void: '#0A0A0A',
    charcoal: '#1E1E1E',
    gold: '#C4A545',
    goldDim: '#9E8538',
    goldGlow: 'rgba(196,165,69,0.08)',
    bone: '#FAF7F0',
    gray1: '#E8E5DD',
    gray2: '#B8B5AD',
    gray3: '#8A8780',
  },
  fonts: {
    display: "'Syne', sans-serif",
    body: "'DM Sans', sans-serif",
    mono: "'Space Mono', monospace",
  },
  spacing: {
    xs: '8px',
    sm: '16px',
    md: '24px',
    lg: '32px',
    xl: '48px',
  },
  animation: {
    fast: '200ms',
    normal: '400ms',
    slow: '800ms',
  },
};
```

**Cursor Prompts for Phase 3** (see Section 5)

---

### Phase 4: Integration & Testing (Week 5)

**Goal**: Connect all components and test end-to-end flow

**Tasks**:
1. Frontend ↔ Backend WebSocket integration
2. Audio recording → backend upload
3. Full pipeline test (story → artwork)
4. Error handling verification
5. Performance optimization

**Test Scenarios**:

1. **Happy Path**:
   - Customer taps screen
   - Records 25-second story
   - Artwork generates in <30s
   - Print initiated
   - Success screen shown

2. **Error Cases**:
   - No audio captured → retry prompt
   - Generation fails → fallback to preset
   - Print queue full → queue message
   - WebSocket disconnect → auto-reconnect
   - System overload → graceful degradation

3. **Edge Cases**:
   - Very quiet audio
   - Background noise
   - Incomplete sentence
   - Multiple languages
   - Inappropriate content

**Performance Targets**:
- WebSocket latency: <50ms
- Audio upload: <2s
- Transcription: <5s
- Prompt generation: <3s
- Image generation: <20s
- Total time: <30s

**Cursor Prompts for Phase 4** (see Section 5)

---

### Phase 5: Print Integration (Week 6)

**Goal**: Integrate Windows print system and DTF printer

**Components**:
1. Windows print API wrapper
2. Print queue management
3. Print status monitoring
4. Heat press timer integration
5. Product selection logic

**Print Workflow**:
```
Image Ready → Resize/Format → Send to DTF → 
Monitor Queue → Transfer Complete → 
Heat Press Timer → Product Complete
```

**`print_controller.py`**:
```python
import win32print
import win32ui
from PIL import Image
from pathlib import Path
from typing import Optional

class PrintController:
    def __init__(self, printer_name: str):
        self.printer_name = printer_name
        self.queue = []
    
    async def print_design(
        self, 
        image_path: Path, 
        product_type: str,
        session_id: str
    ) -> dict:
        """Send design to DTF printer"""
        
        # Resize based on product
        resized = await self._resize_for_product(image_path, product_type)
        
        # Create print job
        job_id = await self._create_print_job(resized)
        
        # Track status
        self.queue.append({
            "job_id": job_id,
            "session_id": session_id,
            "status": "queued",
            "product": product_type
        })
        
        return {"job_id": job_id, "estimated_time": 180}
    
    async def _resize_for_product(self, image_path: Path, product: str) -> Path:
        """Resize image to product dimensions"""
        sizes = {
            "tshirt": (2400, 3200),  # 10x12 inches at 300 DPI
            "tote": (3000, 3000),
            "cap": (2100, 1800),
        }
        
        img = Image.open(image_path)
        img = img.resize(sizes[product], Image.Resampling.LANCZOS)
        
        output_path = image_path.parent / f"{product}_{image_path.name}"
        img.save(output_path, "PNG", dpi=(300, 300))
        
        return output_path
```

**Cursor Prompts for Phase 5** (see Section 5)

---

### Phase 6: Mobile Optimization (Week 7)

**Goal**: Optimize system for van environment

**Tasks**:
1. Power management (battery + generator)
2. Thermal monitoring & throttling
3. Vibration-resistant file I/O
4. Network fallback (mobile hotspot backup)
5. Automatic recovery from power loss

**Mobile-Specific Features**:

**`utils/power_manager.py`**:
```python
import psutil
from dataclasses import dataclass

@dataclass
class PowerStatus:
    on_battery: bool
    battery_percent: float
    time_remaining: int  # seconds
    should_throttle: bool

class PowerManager:
    def __init__(self):
        self.throttle_threshold = 30  # Throttle below 30%
    
    def get_status(self) -> PowerStatus:
        battery = psutil.sensors_battery()
        
        return PowerStatus(
            on_battery=not battery.power_plugged,
            battery_percent=battery.percent,
            time_remaining=battery.secsleft,
            should_throttle=battery.percent < self.throttle_threshold
        )
    
    async def optimize_for_battery(self):
        """Reduce GPU power when on battery"""
        if self.get_status().should_throttle:
            # Reduce SDXL steps from 30 to 20
            # Lower Whisper model to tiny
            # Disable audio playback
            pass
```

**Thermal Management**:
```python
class ThermalManager:
    def __init__(self):
        self.max_gpu_temp = 80  # Celsius
        self.max_cpu_temp = 75
    
    async def monitor_temps(self):
        """Monitor and throttle if overheating"""
        gpu_temp = self._get_gpu_temp()
        cpu_temp = self._get_cpu_temp()
        
        if gpu_temp > self.max_gpu_temp:
            await self._throttle_generation()
        
        if cpu_temp > self.max_cpu_temp:
            await self._reduce_concurrent_sessions()
```

**Cursor Prompts for Phase 6** (see Section 5)

---

### Phase 7: Production Hardening (Week 8)

**Goal**: Deploy production-ready system with monitoring

**Tasks**:
1. Logging & monitoring dashboard
2. Error reporting & alerts
3. Backup & recovery procedures
4. Performance profiling
5. Documentation & runbooks

**Monitoring Dashboard**:

**`utils/dashboard.py`**:
```python
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Real-time system dashboard"""
    stats = await get_system_stats()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>BOBB System Dashboard</title></head>
    <body>
        <h1>BOBB Mobile Van - System Status</h1>
        <div>
            <h2>Today's Stats</h2>
            <p>Sessions: {stats['sessions_today']}</p>
            <p>Artworks: {stats['artworks_generated']}</p>
            <p>Prints: {stats['prints_completed']}</p>
            <p>Uptime: {stats['uptime_hours']}h</p>
        </div>
        <div>
            <h2>System Health</h2>
            <p>GPU Temp: {stats['gpu_temp']}°C</p>
            <p>CPU Usage: {stats['cpu_percent']}%</p>
            <p>Memory: {stats['memory_used']}/{stats['memory_total']}GB</p>
            <p>Disk Space: {stats['disk_free']}GB free</p>
        </div>
        <div>
            <h2>Active Sessions</h2>
            {render_active_sessions(stats['active_sessions'])}
        </div>
    </body>
    </html>
    """
```

**Error Reporting**:
```python
from datetime import datetime
from pathlib import Path
import json

class ErrorReporter:
    def __init__(self, log_path: Path):
        self.log_path = log_path
    
    async def report(self, error: Exception, context: dict):
        """Log error with full context"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "stack_trace": self._get_stack_trace(error)
        }
        
        # Write to log file
        with open(self.log_path / "errors.jsonl", "a") as f:
            f.write(json.dumps(error_entry) + "\n")
        
        # Check if critical - send alert
        if self._is_critical(error):
            await self._send_alert(error_entry)
```

**Backup Procedures**:

**Daily Backup Script** (`scripts/backup.py`):
```python
import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    """Backup SQLite database"""
    db_path = Path("data/bobb_sessions.db")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"bobb_db_{timestamp}.db"
    
    shutil.copy2(db_path, backup_path)
    
    # Keep only last 30 backups
    cleanup_old_backups(backup_dir, keep=30)

def backup_generated_images():
    """Backup generated artwork"""
    # Similar pattern for images
    pass
```

**Cursor Prompts for Phase 7** (see Section 5)

---

## Cursor AI Workflow

### Setup Instructions

**1. Initial Workspace Configuration**

Create a new Cursor AI workspace:

```bash
# Create project directory
mkdir bobb-mobile-agent
cd bobb-mobile-agent

# Initialize git
git init

# Create folder structure
mkdir -p backend/{models,utils,workflows}
mkdir -p frontend/{src/{components,hooks,store,utils,styles},public/assets}
mkdir -p scripts
mkdir -p docs
mkdir -p tests
```

**2. Cursor AI Settings**

In `.cursorrules` (create at project root):

```
# BOBB Mobile Agent - Cursor AI Rules

## Context
This is a production AI system for a mobile retail van.
- Target: Windows PC (RTX 3060) + Samsung tablets
- Offline-first: All AI runs locally
- Real-time: Customer experience is time-sensitive

## Hardware Context
- GPU: RTX 3060 12GB VRAM
- RAM: 32GB
- Storage: NVMe SSD
- Tablets: Samsung Tab S9 Ultra via ADB

## Code Standards
- Python: Type hints required, async/await for I/O
- TypeScript: Strict mode, no any types
- Error handling: Every external call wrapped in try-catch
- Logging: Structured JSON logs

## File References
When working on any file, always check:
- config.py for settings
- session.py for state machine
- constants.ts for shared values

## AI Models
- Whisper: base model (compromise speed/accuracy)
- Llama3: 8B quantized
- SDXL: 1.0 with custom LoRA

## Testing
- Every function must have error case handling
- WebSocket reconnection is critical
- Power loss recovery is mandatory

## Brand
- Color: Gold (#C4A545) + Black (#0A0A0A)
- Fonts: Syne (display), DM Sans (body), Space Mono (mono)
- Tone: Calm, intentional, no hype
```

---

### Phase-by-Phase Cursor Prompts

#### Phase 1: Backend Core

**Prompt 1.1 — Initial FastAPI Setup**

```
@workspace Create a new FastAPI backend for the BOBB Mobile Agent.

Requirements:
- Main file: backend/main.py
- FastAPI with WebSocket support
- CORS enabled for local development
- Health check endpoint at /health
- WebSocket endpoint at /ws/{tablet_id}

Hardware context:
- Running on Windows 11
- RTX 3060 GPU available
- Port 8420 (tablets connect via ADB)

The server must:
1. Accept WebSocket connections from 2 tablets simultaneously
2. Track session state for each connection
3. Handle graceful disconnection
4. Log all events to SQLite

Start with the basic structure. No AI integration yet.
```

**Prompt 1.2 — Session State Machine**

```
@session.py Create a session state machine for customer interactions.

States:
IDLE → WELCOME → LISTENING → THINKING → GENERATING → 
PREVIEW → PRINTING → SUCCESS → ERROR → RESET → IDLE

Each state should:
- Have entry/exit handlers
- Store transition history
- Handle timeouts
- Support state rollback on error

State durations:
- WELCOME: 3s
- LISTENING: 25s (countdown)
- THINKING: 5-8s
- GENERATING: 15-25s
- PREVIEW: 10s
- PRINTING: 30-60s
- SUCCESS: 5s

@config.py Reference config values
```

**Prompt 1.3 — WebSocket Message Protocol**

```
@main.py Design a WebSocket message protocol for tablet ↔ backend communication.

Message types from tablet:
- connect: {type: "connect", tablet_id: string}
- tap_start: {type: "tap_start"}
- audio_chunk: {type: "audio_chunk", data: base64, chunk_index: number}
- audio_complete: {type: "audio_complete", total_chunks: number}
- cancel: {type: "cancel"}
- reset: {type: "reset"}

Message types to tablet:
- state_change: {type: "state_change", state: string, data: object}
- progress: {type: "progress", percent: number, message: string}
- error: {type: "error", message: string, recoverable: boolean}
- artwork_ready: {type: "artwork_ready", image_url: string}
- print_complete: {type: "print_complete"}

Use Pydantic models for type safety.
```

---

#### Phase 2: AI Pipeline

**Prompt 2.1 — Whisper STT Integration**

```
@audio_processor.py Integrate OpenAI Whisper for local speech-to-text.

Requirements:
- Use whisper.load_model("base") for speed/quality balance
- Accept audio file path as input
- Return: {text: string, confidence: float, duration: number}
- Must run on GPU (fp16=True)
- Handle errors: file not found, empty audio, corrupt file

Hardware context:
- RTX 3060 with 12GB VRAM
- Whisper base model (~500MB)
- Target: <5 seconds for 25-second audio clip

Error handling:
- If very quiet audio → return partial transcript + warning
- If corrupt file → raise AudioProcessingError
- If out of memory → retry with CPU

@config.py Add WHISPER_MODEL_SIZE setting
```

**Prompt 2.2 — Ollama + Llama3 Prompt Generation**

```
@prompt_generator.py Create a prompt generator using Ollama + Llama3.

Input: Customer story (transcribed text)
Output: {
  positive_prompt: string (for SDXL),
  negative_prompt: string,
  style_tags: string[],
  confidence: number
}

System prompt strategy:
- You are a creative director for BOBB
- Convert stories to visual artwork descriptions
- Style: Minimalist, symbolic, cultural Kerala themes
- Output must be SDXL-compatible (no complex scenes)

Cultural knowledge base:
- Kerala cultural elements
- Kannur local references
- Malayalam transliteration
- Indian design motifs

@workflows/cultural_knowledge.json Reference this for context

Hardware context:
- Llama3 8B quantized model via Ollama
- Local inference only
- Target: <3 seconds generation time

Error handling:
- If story is inappropriate → return safe fallback prompt
- If story is too short → expand with cultural context
- If generation fails → use preset prompt library

Include a preset prompt library with 10 high-quality fallback prompts.
```

**Prompt 2.3 — ComfyUI Workflow Automation**

```
@image_generator.py Integrate ComfyUI for SDXL image generation.

Requirements:
- Load workflow from workflows/bobb_sdxl.json
- Inject prompt + negative prompt dynamically
- Queue workflow to ComfyUI API (http://127.0.0.1:8188)
- Poll for completion
- Retrieve generated image

Workflow specs:
- Model: SDXL 1.0
- Sampler: DPM++ 2M Karras
- Steps: 30 (adjustable for battery mode)
- CFG Scale: 7.5
- Size: 1024x1024
- Seed: Random
- LoRA: Kerala cultural elements (if available)

Performance targets:
- Generation time: 15-25 seconds
- GPU utilization: 95%+
- Memory: <11GB VRAM

Error handling:
- If ComfyUI not running → return clear error
- If generation fails → retry once with simpler prompt
- If out of memory → reduce steps to 20
- If timeout (>60s) → cancel and return fallback image

@config.py Add COMFYUI_URL and GENERATION_TIMEOUT settings

Battery mode:
- Reduce steps from 30 → 20
- Lower resolution 1024 → 768
- Single pass (no refinement)
```

**Prompt 2.4 — Pipeline Orchestration**

```
@backend Create a pipeline orchestrator that connects all AI components.

Flow: Audio File → Whisper → Llama3 → SDXL → Image File

@audio_processor.py
@prompt_generator.py  
@image_generator.py

Create: pipeline_orchestrator.py

Requirements:
- Async execution
- Progress callbacks (for WebSocket updates)
- Error recovery at each stage
- Logging for debugging
- Performance metrics

Pipeline class structure:
```python
class Pipeline:
    async def process_story(
        self,
        audio_path: Path,
        session_id: str,
        progress_callback: Callable
    ) -> PipelineResult:
        """Execute full pipeline"""
        pass
```

Progress callbacks:
- Transcribing... (5s)
- Understanding story... (3s)
- Generating artwork... (20s)
- Finalizing image... (2s)

Error recovery:
- Stage 1 fails → return error, allow retry
- Stage 2 fails → use fallback prompt, continue
- Stage 3 fails → retry once, then use preset image

@database.py Log every pipeline execution with timings
```

---

#### Phase 3: Frontend UI

**Prompt 3.1 — React App Scaffolding**

```
@frontend Initialize a new React + TypeScript + Vite project.

Requirements:
- React 18
- TypeScript (strict mode)
- Vite for build
- Tailwind CSS for styling
- Zustand for state management
- Framer Motion for animations

File structure:
src/
├── App.tsx
├── main.tsx
├── components/
│   ├── Screen.tsx (base component)
│   └── screens/ (11 screen components)
├── hooks/
│   ├── useWebSocket.ts
│   └── useAudioRecorder.ts
├── store/
│   └── sessionStore.ts
├── styles/
│   └── theme.ts
└── utils/
    └── constants.ts

BOBB theme tokens (from @styles/theme.ts):
- Colors: Gold (#C4A545), Black (#0A0A0A), Bone (#FAF7F0)
- Fonts: Syne (headings), DM Sans (body), Space Mono (code)
- Spacing scale: 8px base
- Animation: 200ms (fast), 400ms (normal), 800ms (slow)

Target: Samsung Tab S9 Ultra (14.6" 2960x1848)
Orientation: Landscape
Touch-optimized: Large tap targets (72px minimum)
```

**Prompt 3.2 — WebSocket Hook**

```
@hooks/useWebSocket.ts Create a robust WebSocket hook with auto-reconnect.

Requirements:
- Connect to ws://localhost:8420/ws/{tablet_id}
- Auto-reconnect on disconnect (5s delay, max 10 retries)
- Send/receive typed messages (Pydantic models from backend)
- Handle connection states: connecting, connected, disconnected, error
- Queue messages while disconnected
- Heartbeat every 30s

Interface:
```typescript
interface UseWebSocketReturn {
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  sendMessage: (message: Message) => void;
  lastMessage: Message | null;
  reconnect: () => void;
}

export function useWebSocket(tabletId: string): UseWebSocketReturn {
  // Implementation
}
```

Error handling:
- Connection refused → show "Server not ready" screen
- Disconnect during session → queue state, reconnect, resume
- Invalid message → log warning, ignore

@utils/constants.ts Add WS_URL and RECONNECT_CONFIG
```

**Prompt 3.3 — Audio Recording Hook**

```
@hooks/useAudioRecorder.ts Create an audio recording hook using Web Audio API.

Requirements:
- Record audio from microphone
- 25-second max duration with countdown
- Real-time waveform data (9 bars, 120ms interval)
- Output: Blob (webm or wav format)
- Visualize audio levels

Interface:
```typescript
interface UseAudioRecorderReturn {
  isRecording: boolean;
  timeRemaining: number; // seconds
  waveformData: number[]; // 9 values, 0-100 scale
  startRecording: () => Promise<void>;
  stopRecording: () => Blob;
  audioLevel: number; // current level 0-100
}

export function useAudioRecorder(duration: number = 25): UseAudioRecorderReturn {
  // Implementation
}
```

Waveform calculation:
- 9 frequency bands
- Update every 120ms
- Smooth transitions (exponential decay)
- Map 0-255 → 0-100 range

Error handling:
- No microphone permission → show permission screen
- Microphone in use → show error message
- Very quiet audio → show "Speak louder" hint

Audio format:
- Sample rate: 16kHz (Whisper compatible)
- Channels: Mono
- Format: WAV or WebM (server accepts both)
```

**Prompt 3.4 — State Machine Store**

```
@store/sessionStore.ts Create Zustand store for session state management.

State shape:
```typescript
interface SessionState {
  // Screen state
  currentScreen: ScreenType;
  previousScreen: ScreenType | null;
  
  // Session data
  sessionId: string | null;
  transcript: string | null;
  artworkUrl: string | null;
  
  // Timing
  startTime: number | null;
  generationStartTime: number | null;
  totalDuration: number | null;
  
  // Progress
  progressPercent: number;
  progressMessage: string;
  
  // Error
  error: string | null;
  errorRecoverable: boolean;
  
  // Actions
  setScreen: (screen: ScreenType) => void;
  setTranscript: (text: string) => void;
  setArtwork: (url: string) => void;
  updateProgress: (percent: number, message: string) => void;
  setError: (message: string, recoverable: boolean) => void;
  reset: () => void;
}
```

Screen types:
'idle' | 'welcome' | 'listening' | 'thinking' | 'generating' | 
'preview' | 'printing' | 'success' | 'error'

Middleware:
- Log every state change
- Persist current screen to localStorage
- Emit analytics events

@utils/constants.ts Reference screen names
```

**Prompt 3.5 — Screen Components**

```
@components/screens Create all 11 screen components with BOBB styling.

Screens:
1. IdleScreen - Gold pulsing animation, "Tap to start"
2. WelcomeScreen - Welcome message, auto-advance to listening
3. ListeningScreen - Waveform, countdown timer, "I'm listening"
4. ThinkingScreen - Gentle animation, "Understanding your story..."
5. GeneratingScreen - Progress bar, "Creating your artwork..."
6. PreviewScreen - Show artwork, "Your design is ready"
7. PrintingScreen - Progress animation, "Printing now..."
8. SuccessScreen - Success animation, "Come back soon!"
9. ErrorScreen - Error message + retry button

Each screen should:
- Use BOBB theme (@styles/theme.ts)
- Be touch-optimized (large tap targets)
- Have enter/exit animations (Framer Motion)
- Be responsive to tablet size
- Handle timeout auto-advance where needed

@components/Screen.tsx Base component with shared layout

Example - IdleScreen:
- Full-screen black background
- Center: BOBB logo (gold)
- Pulsing gold ring animation (2s loop)
- "Tap anywhere to begin" in DM Sans 24px
- On tap → transition to WELCOME

Example - ListeningScreen:
- @components/Waveform.tsx for audio visualization
- @components/Timer.tsx showing countdown from 25
- Gentle gold glow effect
- "I'm listening..." in Syne 32px
```

---

#### Phase 4: Integration Testing

**Prompt 4.1 — End-to-End Test**

```
@tests Create end-to-end test for complete customer journey.

Test flow:
1. Open tablet UI
2. Connect to WebSocket
3. Tap to start
4. Record 25s audio (use test audio file)
5. Verify state transitions:
   idle → welcome → listening → thinking → generating → preview
6. Check artwork is generated
7. Verify print initiated
8. Confirm success screen

Use pytest for backend tests.
Use Playwright for frontend tests.

@backend/main.py
@frontend/src/App.tsx

Test fixtures:
- Test audio files (3 samples: clear, quiet, noisy)
- Mock WebSocket server
- Mock ComfyUI responses

Success criteria:
- All state transitions occur
- No errors logged
- Total time <35 seconds
- Artwork file created

Create: tests/e2e_test.py
```

**Prompt 4.2 — Error Recovery Tests**

```
@tests Create comprehensive error recovery tests.

Scenarios:
1. WebSocket disconnect during recording
   - Expected: Reconnect, resume session
   
2. Whisper transcription returns empty
   - Expected: Show retry prompt
   
3. ComfyUI generation fails
   - Expected: Retry once, then fallback image
   
4. Print queue full
   - Expected: Show "Please wait" message
   
5. Power loss during generation
   - Expected: Resume from last checkpoint on restart
   
6. Very quiet audio
   - Expected: Process with warning, allow retry
   
7. Inappropriate content detected
   - Expected: Use safe fallback, log incident

Each test should verify:
- Correct error message shown
- System recovers automatically where possible
- Session state preserved
- No crashes or hangs

Create: tests/error_recovery_test.py
```

---

#### Phase 5: Print Integration

**Prompt 5.1 — Windows Print Controller**

```
@print_controller.py Integrate Windows printing system for DTF printer.

Requirements:
- Detect installed DTF printer
- Resize image to product dimensions
- Send to print queue
- Monitor print status
- Handle print errors

Product dimensions (at 300 DPI):
- T-shirt: 10"×12" (3000×3600 px)
- Tote bag: 10"×10" (3000×3000 px)
- Cap: 7"×6" (2100×1800 px)

Image processing:
- Convert to CMYK color space
- Add 0.125" bleed
- Embed color profile
- Set print resolution metadata

Windows print API:
```python
import win32print
import win32ui
from PIL import Image

def send_to_printer(image_path: Path, printer_name: str):
    # Implementation
    pass
```

Error handling:
- Printer not found → list available printers
- Out of ink → show alert to staff
- Paper jam → pause queue, alert staff
- Print failed → retry once, then manual intervention

@config.py Add PRINTER_NAME and PRODUCT_SIZES settings
```

---

#### Phase 6: Mobile Optimization

**Prompt 6.1 — Power Management**

```
@utils/power_manager.py Create power management system for van operation.

Requirements:
- Monitor battery status (psutil)
- Detect power source (battery vs generator)
- Adjust performance based on power
- Alert staff when battery low
- Graceful shutdown on critical battery

Battery modes:
- Plugged in: Full performance
- Battery >50%: Normal performance
- Battery 30-50%: Reduced performance
- Battery <30%: Emergency mode
- Battery <10%: Graceful shutdown

Performance adjustments (battery mode):
- SDXL steps: 30 → 20
- Whisper model: base → tiny
- Screen brightness: 100% → 60%
- Background tasks: paused
- Audio playback: disabled

Monitoring:
- Check battery every 30s
- Log power events
- Send alerts via WebSocket

Interface:
```python
class PowerManager:
    def get_status() -> PowerStatus
    async def enable_battery_mode()
    async def enable_performance_mode()
    async def shutdown_gracefully()
```

@config.py Add BATTERY_THRESHOLDS settings
```

**Prompt 6.2 — Thermal Management**

```
@utils/thermal_manager.py Create thermal monitoring and throttling system.

Requirements:
- Monitor GPU temperature (nvidia-smi)
- Monitor CPU temperature (psutil)
- Throttle when overheating
- Alert staff to cooling issues
- Emergency shutdown at critical temp

Temperature thresholds:
- GPU: Normal <75°C, Warn 75-80°C, Critical >80°C
- CPU: Normal <70°C, Warn 70-75°C, Critical >75°C

Throttling actions:
- Reduce concurrent sessions
- Lower SDXL steps
- Pause non-critical processes
- Increase fan speed (if controllable)

Van-specific considerations:
- Summer heat in Kerala (up to 40°C ambient)
- Direct sunlight on van
- Limited ventilation when doors closed
- Generator heat contribution

Monitoring:
- Check temps every 10s
- Log thermal events
- Send alerts when throttling
- Auto-recover when temps normalize

@config.py Add THERMAL_THRESHOLDS settings
```

---

#### Phase 7: Production Deployment

**Prompt 7.1 — System Dashboard**

```
@utils/dashboard.py Create a real-time monitoring dashboard.

Requirements:
- FastAPI route at /dashboard
- HTML page (no external dependencies)
- Real-time updates via WebSocket
- Display key metrics
- Mobile-responsive

Metrics to show:
- Current status (online/offline)
- Sessions today
- Artworks generated
- Prints completed
- System uptime
- GPU temperature
- CPU usage
- Memory usage
- Disk space
- Error count
- Active sessions

Auto-refresh: Every 5 seconds

Interface for staff:
- Quick health check view
- Can reset system if needed
- View recent errors
- See customer queue

Styling: Match BOBB theme (gold on black)

@main.py Add dashboard route
```

**Prompt 7.2 — Startup Script**

```
@scripts Create Windows startup script and service.

Requirements:
- Auto-start on boot
- Launch backend server
- Launch ComfyUI
- Launch Ollama
- Verify all services running
- Open dashboard in browser

Create:
1. startup.bat - Main startup script
2. install_service.bat - Register as Windows service
3. monitor.bat - Health check script (runs every 5 min)

startup.bat should:
- Check GPU is available
- Load all AI models
- Start backend server
- Wait for services ready
- Open staff dashboard
- Log all actions

Health checks:
- Backend API responding
- ComfyUI API responding
- Ollama responding
- GPU accessible
- Disk space >10GB
- No critical errors

If any check fails:
- Log error
- Attempt auto-recovery
- Alert staff if recovery fails

Service configuration:
- Service name: BOBBAgent
- Start type: Automatic
- Recovery: Restart on failure
```

**Prompt 7.3 — Documentation**

```
@docs Create comprehensive operational documentation.

Documents to create:

1. SETUP.md - Initial setup guide
   - Hardware requirements
   - Software installation
   - Model downloads
   - Configuration
   - First run test

2. OPERATIONS.md - Daily operations
   - Morning startup procedure
   - System health checks
   - Troubleshooting common issues
   - Evening shutdown procedure

3. MAINTENANCE.md - Weekly/monthly tasks
   - Database backups
   - Log rotation
   - Model updates
   - Performance optimization
   - Cleaning procedures

4. TROUBLESHOOTING.md - Error resolution
   - Error codes and meanings
   - Step-by-step fixes
   - When to call support
   - Emergency procedures

5. API_REFERENCE.md - Technical reference
   - WebSocket protocol
   - State machine states
   - Configuration options
   - Logging format

Include:
- Screenshots where helpful
- Code examples for common tasks
- Command reference
- Contact information

Style: Clear, concise, staff-friendly
Format: Markdown with table of contents
```

---

## Component Specifications

### Backend API Specification

#### Endpoints

**WebSocket: `/ws/{tablet_id}`**

Connect a tablet to the backend.

**Messages from tablet**:
```json
{
  "type": "connect",
  "tablet_id": "tablet-1",
  "version": "1.0.0"
}

{
  "type": "tap_start",
  "timestamp": 1234567890
}

{
  "type": "audio_chunk",
  "data": "base64_encoded_audio",
  "chunk_index": 0,
  "total_chunks": 10
}

{
  "type": "audio_complete",
  "session_id": "sess_abc123"
}

{
  "type": "cancel",
  "session_id": "sess_abc123"
}

{
  "type": "reset"
}
```

**Messages to tablet**:
```json
{
  "type": "state_change",
  "state": "listening",
  "data": {
    "duration": 25,
    "message": "I'm listening..."
  }
}

{
  "type": "progress",
  "percent": 45,
  "stage": "generating",
  "message": "Creating artwork...",
  "eta_seconds": 12
}

{
  "type": "error",
  "code": "AUDIO_PROCESSING_FAILED",
  "message": "Couldn't hear that clearly. Try again?",
  "recoverable": true
}

{
  "type": "artwork_ready",
  "image_url": "/outputs/sess_abc123.png",
  "preview_url": "/outputs/sess_abc123_thumb.png"
}

{
  "type": "print_complete",
  "session_id": "sess_abc123",
  "product_type": "tshirt"
}
```

#### REST Endpoints

**GET `/health`**

System health check.

Response:
```json
{
  "status": "healthy",
  "services": {
    "whisper": "ready",
    "ollama": "ready",
    "comfyui": "ready",
    "printer": "ready"
  },
  "system": {
    "gpu_temp": 72,
    "cpu_usage": 45,
    "memory_used": 18.5,
    "disk_free": 245
  }
}
```

**GET `/dashboard`**

Staff monitoring dashboard (HTML).

**GET `/metrics`**

Prometheus-style metrics for monitoring.

**GET `/outputs/{session_id}.png`**

Retrieve generated artwork image.

---

### Frontend Component Specification

#### Screen Components

All screens inherit from `Screen` base component:

```tsx
interface ScreenProps {
  onNext?: () => void;
  onError?: (error: string) => void;
  onReset?: () => void;
  data?: Record<string, any>;
}

export default function Screen(props: ScreenProps) {
  return (
    <div className="screen-container">
      {/* Screen content */}
    </div>
  );
}
```

#### Screen Styling

```css
.screen-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0A0A0A;
  color: #FAF7F0;
  padding: 48px;
  font-family: 'DM Sans', sans-serif;
}

.screen-title {
  font-family: 'Syne', sans-serif;
  font-size: 48px;
  font-weight: 600;
  color: #C4A545;
  margin-bottom: 24px;
  text-align: center;
}

.screen-message {
  font-size: 24px;
  color: #E8E5DD;
  text-align: center;
  max-width: 800px;
  line-height: 1.6;
}

.tap-target {
  min-width: 72px;
  min-height: 72px;
  touch-action: manipulation;
  cursor: pointer;
}
```

---

## Deployment Strategy

### Production Checklist

**Week Before Launch**:
- [ ] Hardware installed in van
- [ ] All cables secured (vibration-proof)
- [ ] Power system tested (generator + UPS)
- [ ] Tablets mounted securely
- [ ] Network tested (offline + fallback)
- [ ] All AI models downloaded and verified
- [ ] Print workflow tested end-to-end
- [ ] Staff trained on operations
- [ ] Emergency procedures documented
- [ ] Backup system ready

**Launch Day**:
- [ ] Full system test (morning)
- [ ] Staff walkthrough
- [ ] First customer dry-run
- [ ] Monitoring dashboard open
- [ ] Mobile hotspot backup ready
- [ ] Print supplies stocked
- [ ] Emergency contacts confirmed

**Post-Launch**:
- [ ] Daily performance logs reviewed
- [ ] Customer feedback collected
- [ ] Error rates monitored
- [ ] Hardware temps tracked
- [ ] System optimizations identified

---

### Monitoring & Maintenance

**Daily Tasks**:
- Morning system health check
- Review previous day's logs
- Clear any error alerts
- Check disk space
- Verify print supplies
- Test generation pipeline
- Backup database

**Weekly Tasks**:
- Full system restart
- Windows updates
- Clear temp files
- Review performance metrics
- Check for model updates
- Test backup restore
- Review error patterns

**Monthly Tasks**:
- Deep clean hardware
- Update documentation
- Review and optimize prompts
- Analyze customer patterns
- Plan improvements
- Staff refresher training

---

## Testing & Quality Assurance

### Test Suites

**Unit Tests** (`tests/unit/`):
- Audio processing functions
- Prompt generation logic
- State machine transitions
- WebSocket message handling
- Image resizing functions

**Integration Tests** (`tests/integration/`):
- Backend API endpoints
- WebSocket full flow
- AI pipeline (mocked models)
- Database operations
- Print controller

**End-to-End Tests** (`tests/e2e/`):
- Complete customer journey
- Error recovery scenarios
- Multi-user concurrent sessions
- Power loss recovery
- Network failure handling

**Performance Tests** (`tests/performance/`):
- Generation time under load
- WebSocket throughput
- Memory usage over time
- GPU utilization
- Concurrent session limits

### Test Data

**Audio Samples** (`tests/fixtures/audio/`):
- `clear_25s.wav` - Perfect quality test
- `quiet_20s.wav` - Quiet voice test
- `noisy_25s.wav` - Background noise test
- `short_10s.wav` - Too-short test
- `silence_25s.wav` - No speech test

**Test Stories** (`tests/fixtures/stories.json`):
```json
[
  {
    "id": "clear_story",
    "text": "I grew up in Kannur, by the beach. Every evening, my grandmother and I would walk along the shore and collect seashells. She would tell me stories about each one.",
    "expected_themes": ["beach", "family", "Kerala", "nostalgia"]
  },
  {
    "id": "short_story",
    "text": "My favorite color is blue.",
    "expected_themes": ["color", "simple"],
    "should_expand": true
  }
]
```

---

## Appendices

### Appendix A: File Tree

Complete file structure:

```
bobb-mobile-agent/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── session.py
│   ├── audio_processor.py
│   ├── prompt_generator.py
│   ├── image_generator.py
│   ├── print_controller.py
│   ├── database.py
│   ├── pipeline_orchestrator.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session_model.py
│   │   ├── message_model.py
│   │   └── result_model.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── health_monitor.py
│   │   ├── power_manager.py
│   │   ├── thermal_manager.py
│   │   └── dashboard.py
│   └── workflows/
│       ├── bobb_sdxl.json
│       ├── cultural_knowledge.json
│       └── fallback_prompts.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── Screen.tsx
│   │   │   ├── Waveform.tsx
│   │   │   ├── Timer.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── screens/
│   │   │       ├── IdleScreen.tsx
│   │   │       ├── WelcomeScreen.tsx
│   │   │       ├── ListeningScreen.tsx
│   │   │       ├── ThinkingScreen.tsx
│   │   │       ├── GeneratingScreen.tsx
│   │   │       ├── PreviewScreen.tsx
│   │   │       ├── PrintingScreen.tsx
│   │   │       ├── SuccessScreen.tsx
│   │   │       └── ErrorScreen.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useAudioRecorder.ts
│   │   │   └── useSessionState.ts
│   │   ├── store/
│   │   │   └── sessionStore.ts
│   │   ├── styles/
│   │   │   ├── theme.ts
│   │   │   └── global.css
│   │   └── utils/
│   │       ├── audio.ts
│   │       ├── constants.ts
│   │       └── websocket.ts
│   ├── public/
│   │   └── assets/
│   │       ├── logo.svg
│   │       └── animations/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── scripts/
│   ├── startup.bat
│   ├── install_service.bat
│   ├── monitor.bat
│   ├── backup.py
│   └── deploy.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── performance/
│   └── fixtures/
│       ├── audio/
│       ├── images/
│       └── stories.json
├── docs/
│   ├── SETUP.md
│   ├── OPERATIONS.md
│   ├── MAINTENANCE.md
│   ├── TROUBLESHOOTING.md
│   └── API_REFERENCE.md
├── data/
│   ├── bobb_sessions.db
│   └── logs/
├── outputs/
│   ├── generated/
│   └── printed/
├── .cursorrules
├── .gitignore
├── requirements.txt
├── package.json
└── README.md
```

### Appendix B: Configuration Reference

**`config.py`** (Backend Configuration):

```python
import os
from pathlib import Path

class Config:
    # Server
    HOST = "0.0.0.0"
    PORT = 8420
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    OUTPUTS_DIR = BASE_DIR / "outputs"
    LOGS_DIR = DATA_DIR / "logs"
    
    # AI Models
    WHISPER_MODEL = "base"  # tiny, base, small, medium
    WHISPER_DEVICE = "cuda"
    LLAMA_MODEL = "llama3:8b"
    COMFYUI_URL = "http://127.0.0.1:8188"
    
    # Generation Settings
    SDXL_STEPS = 30
    SDXL_CFG = 7.5
    SDXL_SIZE = 1024
    GENERATION_TIMEOUT = 60  # seconds
    
    # Audio Settings
    RECORDING_DURATION = 25  # seconds
    SAMPLE_RATE = 16000
    AUDIO_FORMAT = "wav"
    
    # Session Settings
    SESSION_TIMEOUT = 300  # 5 minutes
    MAX_CONCURRENT_SESSIONS = 2
    
    # Print Settings
    PRINTER_NAME = "DTF Printer"
    PRODUCT_SIZES = {
        "tshirt": (3000, 3600),
        "tote": (3000, 3000),
        "cap": (2100, 1800)
    }
    
    # Power Management
    BATTERY_THRESHOLDS = {
        "normal": 50,
        "reduced": 30,
        "emergency": 10
    }
    
    # Thermal Management
    MAX_GPU_TEMP = 80  # Celsius
    MAX_CPU_TEMP = 75
    
    # Database
    DATABASE_URL = f"sqlite:///{DATA_DIR}/bobb_sessions.db"
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "json"
```

---

### Appendix C: Error Codes

**System Errors** (1xxx):
- `1001`: System startup failed
- `1002`: GPU not available
- `1003`: Out of memory
- `1004`: Disk space critical
- `1005`: Service unreachable

**Audio Errors** (2xxx):
- `2001`: Microphone permission denied
- `2002`: No audio detected
- `2003`: Audio too quiet
- `2004`: Corrupt audio file
- `2005`: Recording failed

**AI Errors** (3xxx):
- `3001`: Transcription failed
- `3002`: Prompt generation failed
- `3003`: Image generation failed
- `3004`: Generation timeout
- `3005`: Model not loaded

**Print Errors** (4xxx):
- `4001`: Printer not found
- `4002`: Print queue full
- `4003`: Out of supplies
- `4004`: Print job failed
- `4005`: Printer offline

**Network Errors** (5xxx):
- `5001`: WebSocket disconnected
- `5002`: Connection timeout
- `5003`: Invalid message format
- `5004`: Rate limit exceeded
- `5005`: Authentication failed

---

### Appendix D: Performance Targets

**Response Times**:
- WebSocket message latency: <50ms
- Audio upload: <2s
- Whisper transcription: <5s
- Llama3 prompt: <3s
- SDXL generation: <25s
- Print initiation: <1s
- Total experience: <35s

**System Resources**:
- GPU VRAM usage: <11GB
- RAM usage: <24GB
- CPU usage: <70% average
- Disk I/O: <100MB/s
- Network: 100Mbps

**Reliability**:
- Uptime: 99.5%
- Error rate: <2%
- Auto-recovery: >95%
- Data loss: 0%

**Throughput**:
- Concurrent sessions: 2
- Sessions per hour: 20
- Daily capacity: 120-150
- Generation queue: 5

---

### Appendix E: Cultural Knowledge Base

**Kerala Cultural Elements** (`workflows/cultural_knowledge.json`):

```json
{
  "regions": {
    "kannur": {
      "themes": ["theyyam", "beaches", "handloom", "spices"],
      "colors": ["red", "gold", "earth tones"],
      "motifs": ["palm trees", "waves", "traditional masks"]
    }
  },
  "festivals": [
    "theyyam", "onam", "vishu", "thrissur pooram"
  ],
  "art_forms": [
    "kathakali", "theyyam", "kalaripayattu", "mural painting"
  ],
  "symbols": {
    "elephant": "wisdom, strength",
    "peacock": "beauty, pride",
    "lamp": "knowledge, prosperity",
    "lotus": "purity, enlightenment"
  },
  "design_principles": [
    "Minimalist symbolism",
    "Strong cultural anchors",
    "Avoid literal representation",
    "Use negative space",
    "Single focal element"
  ]
}
```

---

### Appendix F: Prompt Templates

**Fallback Prompts** (`workflows/fallback_prompts.json`):

High-quality preset prompts for when generation fails:

```json
[
  {
    "id": "kerala_beach",
    "prompt": "Minimalist line art illustration of Kerala beach scene, single palm tree silhouette, warm sunset gradient, abstract waves, high contrast, gold and black color scheme, symbolic representation",
    "negative": "realistic, photograph, complex details, multiple elements, text, watermark"
  },
  {
    "id": "theyyam_abstract",
    "prompt": "Abstract geometric interpretation of Theyyam mask, bold angular shapes, traditional Kerala art influence, red and gold accent colors, strong contrast, symbolic design, modern minimalism",
    "negative": "realistic face, photograph, detailed textures, multiple elements"
  },
  {
    "id": "monsoon_pattern",
    "prompt": "Stylized rain pattern inspired by Kerala monsoon, geometric raindrops, organic flow, muted earth tones with gold accents, symbolic water element, clean lines, negative space",
    "negative": "realistic clouds, photograph, complex scenery, text"
  }
]
```

---

## Next Steps

### Immediate Actions (Next 48 Hours)

1. **Setup Development Environment**:
   - Install Python 3.11 and Node.js 20
   - Install CUDA toolkit
   - Download Whisper, Llama3, SDXL models
   - Test GPU availability

2. **Create Project Structure**:
   - Initialize git repository
   - Create folder structure (see Appendix A)
   - Setup `.cursorrules` file
   - Create `config.py` with your settings

3. **Start Phase 1**:
   - Begin with Backend Core
   - Use Cursor prompts from Section 5
   - Commit after each working component
   - Test as you build

### Weekly Goals

**Week 1**: Backend Core + Session State Machine  
**Week 2**: AI Pipeline Integration  
**Week 3**: Frontend UI (all screens)  
**Week 4**: Full Integration + Testing  
**Week 5**: Print Integration  
**Week 6**: Mobile Optimization  
**Week 7**: Production Hardening  
**Week 8**: Deployment + Staff Training  

### Success Milestones

✅ **Day 7**: Backend server running, WebSocket working  
✅ **Day 14**: AI pipeline generates artwork from test audio  
✅ **Day 21**: Tablet UI connects and completes full flow  
✅ **Day 28**: End-to-end test passes (tap → artwork → print)  
✅ **Day 35**: Print integration working  
✅ **Day 42**: Mobile optimizations complete  
✅ **Day 49**: Production-ready, all tests passing  
✅ **Day 56**: Deployed in van, first live customer session  

---

## Support & Resources

**Documentation**:
- FastAPI: https://fastapi.tiangolo.com
- React: https://react.dev
- ComfyUI: https://github.com/comfyanonymous/ComfyUI
- Ollama: https://ollama.ai
- Whisper: https://github.com/openai/whisper

**Community**:
- ComfyUI Discord for workflow help
- r/LocalLLaMA for model optimization
- FastAPI Discord for backend questions

**Hardware**:
- NVIDIA: CUDA documentation
- Windows: Print API documentation

---

**Document Version**: 1.0  
**Last Updated**: May 2026  
**Status**: Ready for Development

---

_This plan is designed for Cursor AI implementation. Each phase includes copy-paste-ready prompts. Follow the phases sequentially for best results._
