# ============================================================================
# BOBB AI PLATFORM - SESSION MANAGER & DATABASE SERVICES
# State management and persistent data layer
# ============================================================================

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import uuid
import threading

logger = logging.getLogger(__name__)

# ============================================================================
# SESSION STATE MACHINE
# ============================================================================

class SessionState(str, Enum):
    """Complete state machine for BOBB sessions"""
    IDLE = "IDLE"
    GREETING = "GREETING"
    LISTENING = "LISTENING"
    CLARIFYING = "CLARIFYING"
    THINKING = "THINKING"
    GENERATING = "GENERATING"
    PREVIEW = "PREVIEW"
    REFINING = "REFINING"
    PRODUCT_SELECTION = "PRODUCT_SELECTION"
    CART = "CART"
    CHECKOUT = "CHECKOUT"
    PRODUCTION = "PRODUCTION"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    HELP = "HELP"

# Valid state transitions
STATE_TRANSITIONS = {
    SessionState.IDLE: [SessionState.GREETING],
    SessionState.GREETING: [SessionState.LISTENING],
    SessionState.LISTENING: [SessionState.CLARIFYING, SessionState.THINKING],
    SessionState.CLARIFYING: [SessionState.LISTENING, SessionState.THINKING],
    SessionState.THINKING: [SessionState.GENERATING],
    SessionState.GENERATING: [SessionState.PREVIEW],
    SessionState.PREVIEW: [SessionState.REFINING, SessionState.PRODUCT_SELECTION],
    SessionState.REFINING: [SessionState.GENERATING, SessionState.PRODUCT_SELECTION],
    SessionState.PRODUCT_SELECTION: [SessionState.CART],
    SessionState.CART: [SessionState.CHECKOUT, SessionState.PRODUCT_SELECTION],
    SessionState.CHECKOUT: [SessionState.PRODUCTION, SessionState.ERROR],
    SessionState.PRODUCTION: [SessionState.SUCCESS, SessionState.ERROR],
    SessionState.SUCCESS: [SessionState.IDLE],
    SessionState.ERROR: [SessionState.THINKING, SessionState.HELP, SessionState.IDLE],
    SessionState.HELP: [SessionState.THINKING, SessionState.IDLE]
}

# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """
    Manages BOBB user sessions
    - Session lifecycle (create, update, delete)
    - State transitions
    - Context preservation
    - Session timeout handling
    """
    
    def __init__(self, db_path: str = "bobb_sessions.db"):
        self.db_path = db_path
        self.sessions = {}  # In-memory session cache
        self.lock = threading.Lock()
        
        logger.info(f"SessionManager initialized with DB: {db_path}")
    
    async def create_session(self, session_id: str = None, customer_name: str = None) -> Dict:
        """Create a new session"""
        
        if session_id is None:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        session = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "current_state": SessionState.IDLE,
            "customer_name": customer_name,
            "customer_phone": None,
            "customer_email": None,
            "duration_seconds": 0,
            "completed": False,
            "satisfaction_score": None,
            "notes": "",
            # Context data
            "story": None,
            "design_prompt": None,
            "design_images": [],
            "selected_design_variant": None,
            "design_id": None,
            "selected_product": None,
            "cart_items": [],
            "order_id": None,
            "production_job_id": None,
            # Interaction tracking
            "conversation_turns": [],
            "refinement_count": 0,
            "max_refinements": 3,
            "clarification_count": 0,
            "max_clarifications": 2,
            "error_count": 0
        }
        
        with self.lock:
            self.sessions[session_id] = session
        
        logger.info(f"✓ Session created: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        
        with self.lock:
            session = self.sessions.get(session_id)
        
        if session:
            # Check timeout (30 minutes)
            created = datetime.fromisoformat(session["created_at"])
            if (datetime.now() - created).total_seconds() > 1800:
                logger.warning(f"Session timed out: {session_id}")
                await self.abandon_session(session_id)
                return None
        
        return session
    
    async def update_state(self, session_id: str, new_state: str) -> bool:
        """
        Update session state with validation
        Validates state transitions
        """
        
        session = await self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False
        
        current_state = SessionState(session["current_state"])
        try:
            new_state_enum = SessionState(new_state)
        except ValueError:
            logger.error(f"Invalid state: {new_state}")
            return False
        
        # Validate transition
        if new_state_enum not in STATE_TRANSITIONS.get(current_state, []):
            logger.warning(f"Invalid transition: {current_state} → {new_state_enum}")
            return False
        
        with self.lock:
            self.sessions[session_id]["current_state"] = new_state_enum
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"State transition: {current_state} → {new_state_enum} ({session_id})")
        return True
    
    async def update_context(self, session_id: str, context_key: str, value: any) -> bool:
        """Update session context (story, design, etc.)"""
        
        session = await self.get_session(session_id)
        if not session:
            return False
        
        with self.lock:
            if context_key in session:
                session[context_key] = value
                session["updated_at"] = datetime.now().isoformat()
            else:
                logger.warning(f"Unknown context key: {context_key}")
                return False
        
        return True
    
    async def add_conversation_turn(self, session_id: str, role: str, content: str):
        """Add conversation turn (for logging/context)"""
        
        session = await self.get_session(session_id)
        if not session:
            return
        
        turn = {
            "timestamp": datetime.now().isoformat(),
            "role": role,  # "customer" or "agent"
            "content": content
        }
        
        with self.lock:
            if "conversation_turns" not in session:
                session["conversation_turns"] = []
            session["conversation_turns"].append(turn)
    
    async def increment_refinement_count(self, session_id: str) -> int:
        """Track design refinements (max 3)"""
        
        session = await self.get_session(session_id)
        if not session:
            return 0
        
        with self.lock:
            session["refinement_count"] = session.get("refinement_count", 0) + 1
        
        return session["refinement_count"]
    
    async def increment_clarification_count(self, session_id: str) -> int:
        """Track clarifications (max 2)"""
        
        session = await self.get_session(session_id)
        if not session:
            return 0
        
        with self.lock:
            session["clarification_count"] = session.get("clarification_count", 0) + 1
        
        return session["clarification_count"]
    
    async def complete_session(self, session_id: str, satisfaction_score: int = None) -> Dict:
        """Mark session as complete"""
        
        session = await self.get_session(session_id)
        if not session:
            return None
        
        created = datetime.fromisoformat(session["created_at"])
        duration = (datetime.now() - created).total_seconds()
        
        with self.lock:
            session["completed"] = True
            session["duration_seconds"] = int(duration)
            if satisfaction_score:
                session["satisfaction_score"] = satisfaction_score
            session["updated_at"] = datetime.now().isoformat()
        
        # Persist to database
        await self._persist_session(session)
        
        logger.info(f"✓ Session completed: {session_id} ({duration:.0f}s)")
        return session
    
    async def abandon_session(self, session_id: str):
        """Abandon session without completion"""
        
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
        
        logger.info(f"Session abandoned: {session_id}")
    
    async def _persist_session(self, session: Dict):
        """Persist session to database (async wrapper)"""
        db = DatabaseManager()
        db.save_session(session)
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        with self.lock:
            return list(self.sessions.keys())
    
    async def get_session_summary(self, session_id: str) -> Dict:
        """Get summary of session for analytics"""
        
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session["id"],
            "created_at": session["created_at"],
            "duration_seconds": session["duration_seconds"],
            "completed": session["completed"],
            "customer_name": session["customer_name"],
            "order_id": session.get("order_id"),
            "state": session["current_state"],
            "satisfaction_score": session["satisfaction_score"],
            "refinement_count": session.get("refinement_count", 0),
            "conversation_turns": len(session.get("conversation_turns", []))
        }

# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """
    SQLite database layer
    - Sessions, conversations, designs, orders
    - Production jobs, inventory, analytics
    """
    
    def __init__(self, db_path: str = "bobb_platform.db"):
        self.db_path = db_path
        self.conn = None
        self.init_db()
    
    def init_db(self):
        """Initialize database with all required tables"""
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # ===== SESSIONS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_state TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                customer_email TEXT,
                duration_seconds INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT 0,
                satisfaction_score INTEGER,
                notes TEXT,
                session_data TEXT
            )
        """)
        
        # ===== CONVERSATION LOGS =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                turn_number INTEGER,
                input_type TEXT,
                customer_input TEXT,
                transcript TEXT,
                agent_response TEXT,
                response_time_ms INTEGER,
                model_used TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # ===== DESIGNS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS designs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                design_prompt TEXT,
                design_metadata TEXT,
                image_urls TEXT,
                selected_variant INTEGER,
                refinements_applied INTEGER DEFAULT 0,
                design_locked BOOLEAN DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # ===== ORDERS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT,
                customer_email TEXT,
                total_amount INTEGER,
                discount_amount INTEGER DEFAULT 0,
                discount_type TEXT,
                payment_method TEXT,
                payment_status TEXT DEFAULT 'pending',
                order_status TEXT DEFAULT 'pending',
                completion_time TEXT,
                name_tag_text TEXT,
                order_data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # ===== ORDER ITEMS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                design_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT,
                size TEXT,
                color TEXT,
                quantity INTEGER,
                unit_price INTEGER,
                subtotal INTEGER,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (design_id) REFERENCES designs(id)
            )
        """)
        
        # ===== PRODUCTION JOBS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_jobs (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                order_item_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                design_file_path TEXT,
                printer_model TEXT,
                print_status TEXT DEFAULT 'queued',
                print_progress_percent INTEGER DEFAULT 0,
                print_duration_seconds INTEGER,
                press_status TEXT DEFAULT 'queued',
                press_progress_percent INTEGER DEFAULT 0,
                press_duration_seconds INTEGER,
                stitch_status TEXT DEFAULT 'queued',
                stitch_progress_percent INTEGER DEFAULT 0,
                stitch_duration_seconds INTEGER,
                quality_check_passed BOOLEAN,
                notes TEXT,
                job_data TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        
        # ===== INVENTORY TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL UNIQUE,
                product_name TEXT,
                total_units INTEGER,
                units_sold INTEGER DEFAULT 0,
                units_remaining INTEGER,
                reorder_level INTEGER,
                last_reorder_date TEXT,
                supplier_contact TEXT
            )
        """)
        
        # ===== ANALYTICS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL UNIQUE,
                total_sessions INTEGER,
                completed_orders INTEGER,
                failed_orders INTEGER,
                total_revenue INTEGER,
                avg_session_duration_seconds INTEGER,
                avg_satisfaction_score REAL,
                top_product TEXT,
                top_design_theme TEXT,
                printer_uptime_percent REAL,
                analytics_data TEXT
            )
        """)
        
        # ===== AGENT LOGS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                agent_name TEXT,
                agent_version TEXT,
                state TEXT,
                action TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                execution_time_ms INTEGER,
                model_used TEXT,
                confidence_score REAL,
                error_occurred BOOLEAN DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        self.conn.commit()
        logger.info(f"✓ Database initialized: {self.db_path}")
    
    # ===== SESSION OPERATIONS =====
    
    def save_session(self, session: Dict):
        """Save session to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions 
                (id, created_at, updated_at, current_state, customer_name, customer_phone, 
                 customer_email, duration_seconds, completed, satisfaction_score, notes, session_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session["id"],
                session["created_at"],
                session["updated_at"],
                session["current_state"],
                session.get("customer_name"),
                session.get("customer_phone"),
                session.get("customer_email"),
                session.get("duration_seconds", 0),
                session.get("completed", False),
                session.get("satisfaction_score"),
                session.get("notes", ""),
                json.dumps(session)  # Store full session as JSON
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row and row["session_data"]:
                return json.loads(row["session_data"])
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
            return None
    
    # ===== DESIGN OPERATIONS =====
    
    def save_design(self, design_id: str, session_id: str, design_prompt: str, 
                   image_urls: Dict, metadata: Dict = None):
        """Save design to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO designs
                (id, session_id, created_at, design_prompt, design_metadata, image_urls, refinements_applied)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                design_id,
                session_id,
                datetime.now().isoformat(),
                design_prompt,
                json.dumps(metadata or {}),
                json.dumps(image_urls),
                0
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving design: {e}")
    
    def get_design(self, design_id: str) -> Optional[Dict]:
        """Get design by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM designs WHERE id = ?", (design_id,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result["image_urls"] = json.loads(result["image_urls"])
                result["design_metadata"] = json.loads(result["design_metadata"])
                return result
            return None
        except Exception as e:
            logger.error(f"Error retrieving design: {e}")
            return None
    
    def update_design(self, design_id: str, image_url: str):
        """Update design with refined image"""
        try:
            cursor = self.conn.cursor()
            design = self.get_design(design_id)
            
            if design:
                image_urls = design["image_urls"]
                image_urls["refined"] = image_url
                
                cursor.execute("""
                    UPDATE designs 
                    SET image_urls = ?, refinements_applied = refinements_applied + 1
                    WHERE id = ?
                """, (json.dumps(image_urls), design_id))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating design: {e}")
    
    def select_design_variant(self, design_id: str, variant_id: int):
        """Mark a design variant as selected"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE designs 
                SET selected_variant = ?, design_locked = 1
                WHERE id = ?
            """, (variant_id, design_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error selecting variant: {e}")
    
    # ===== ORDER OPERATIONS =====
    
    def create_order(self, order_id: str, session_id: str, customer_name: str, 
                    customer_phone: str, total_amount: int, discount_amount: int = 0,
                    discount_type: str = None, name_tag_text: str = ""):
        """Create new order"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO orders
                (id, session_id, created_at, customer_name, customer_phone, total_amount, 
                 discount_amount, discount_type, name_tag_text, order_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                session_id,
                datetime.now().isoformat(),
                customer_name,
                customer_phone,
                total_amount,
                discount_amount,
                discount_type,
                name_tag_text,
                ""
            ))
            self.conn.commit()
            return order_id
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None
    
    def add_order_item(self, order_id: str, design_id: str, product_id: str, 
                      product_name: str, quantity: int, unit_price: int):
        """Add item to order"""
        try:
            item_id = f"item_{uuid.uuid4().hex[:10]}"
            subtotal = quantity * unit_price
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO order_items
                (id, order_id, design_id, product_id, product_name, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, order_id, design_id, product_id, product_name, quantity, unit_price, subtotal))
            self.conn.commit()
            return item_id
        except Exception as e:
            logger.error(f"Error adding order item: {e}")
            return None
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving order: {e}")
            return None
    
    def update_order_status(self, order_id: str, status: str):
        """Update order status"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE orders 
                SET order_status = ?, updated_at = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), order_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating order: {e}")
    
    # ===== PRODUCTION JOB OPERATIONS =====
    
    def create_production_job(self, job_id: str, order_id: str, order_item_id: str, 
                             design_file_path: str) -> str:
        """Create production job"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO production_jobs
                (id, order_id, order_item_id, created_at, design_file_path)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, order_id, order_item_id, datetime.now().isoformat(), design_file_path))
            self.conn.commit()
            return job_id
        except Exception as e:
            logger.error(f"Error creating production job: {e}")
            return None
    
    def update_job_stage(self, job_id: str, stage: str, status: str, progress: int):
        """Update production job stage progress"""
        try:
            cursor = self.conn.cursor()
            
            if stage == "print":
                cursor.execute("""
                    UPDATE production_jobs
                    SET print_status = ?, print_progress_percent = ?
                    WHERE id = ?
                """, (status, progress, job_id))
            elif stage == "press":
                cursor.execute("""
                    UPDATE production_jobs
                    SET press_status = ?, press_progress_percent = ?
                    WHERE id = ?
                """, (status, progress, job_id))
            elif stage == "stitch":
                cursor.execute("""
                    UPDATE production_jobs
                    SET stitch_status = ?, stitch_progress_percent = ?
                    WHERE id = ?
                """, (status, progress, job_id))
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating job stage: {e}")
    
    def get_production_job(self, job_id: str) -> Optional[Dict]:
        """Get production job by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM production_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving production job: {e}")
            return None
    
    # ===== ANALYTICS OPERATIONS =====
    
    def log_agent_execution(self, session_id: str, agent_name: str, agent_version: str,
                           state: str, action: str, execution_time_ms: int,
                           model_used: str, confidence: float):
        """Log agent execution for analytics"""
        try:
            log_id = f"alog_{uuid.uuid4().hex[:10]}"
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO agent_logs
                (id, session_id, timestamp, agent_name, agent_version, state, action, 
                 execution_time_ms, model_used, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, session_id, datetime.now().isoformat(), agent_name, agent_version,
                 state, action, execution_time_ms, model_used, confidence))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error logging agent: {e}")
    
    def get_daily_analytics(self, date: str = None) -> Optional[Dict]:
        """Get analytics for a specific day"""
        if date is None:
            date = datetime.now().date().isoformat()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM analytics WHERE date = ?", (date,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving analytics: {e}")
            return None
    
    def update_daily_analytics(self):
        """Calculate and update analytics for today"""
        today = datetime.now().date().isoformat()
        
        try:
            cursor = self.conn.cursor()
            
            # Get stats for today
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT id) as total_sessions,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_orders,
                    SUM(CASE WHEN order_status = 'failed' THEN 1 ELSE 0 END) as failed_orders,
                    SUM(total_amount) as total_revenue,
                    AVG(duration_seconds) as avg_duration,
                    AVG(satisfaction_score) as avg_satisfaction
                FROM sessions
                WHERE DATE(created_at) = ?
            """, (today,))
            
            stats = dict(cursor.fetchone())
            
            # Upsert analytics record
            cursor.execute("""
                INSERT OR REPLACE INTO analytics
                (id, date, total_sessions, completed_orders, failed_orders, total_revenue,
                 avg_session_duration_seconds, avg_satisfaction_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"an_{today}", today, stats.get('total_sessions', 0),
                 stats.get('completed_orders', 0), stats.get('failed_orders', 0),
                 stats.get('total_revenue', 0), int(stats.get('avg_duration', 0) or 0),
                 stats.get('avg_satisfaction', 0)))
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
    
    # ===== UTILITY OPERATIONS =====
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product info from inventory"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM inventory WHERE product_id = ?", (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving product: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def demo():
        # Create session manager
        session_mgr = SessionManager()
        
        # Create session
        session = await session_mgr.create_session(customer_name="Arjun")
        print(f"Created session: {session['id']}")
        
        # Update state
        await session_mgr.update_state(session["id"], "GREETING")
        print(f"State: GREETING")
        
        # Add conversation
        await session_mgr.add_conversation_turn(session["id"], "customer", "Hello, I want a t-shirt design")
        print(f"Conversation logged")
        
        # Update context
        await session_mgr.update_context(session["id"], "story", {"themes": ["beach", "hometown"]})
        print(f"Context updated")
        
        # Complete session
        completed = await session_mgr.complete_session(session["id"], satisfaction_score=5)
        print(f"Session completed: {completed['duration_seconds']}s")
        
        # Get summary
        summary = await session_mgr.get_session_summary(session["id"])
        print(json.dumps(summary, indent=2))
    
    asyncio.run(demo())
