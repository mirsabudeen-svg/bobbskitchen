# ============================================================================
# BOBB AI PLATFORM - MULTI-AGENT IMPLEMENTATION
# Production-Grade Agent Code for Conversation, Design, and Commerce
# ============================================================================

import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from enum import Enum
import logging

# AI Libraries
import anthropic  # For Gemini via Claude API
import openai
from PIL import Image
import requests

# Local utilities
logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class Intent(str, Enum):
    """Customer intents that agents can recognize"""
    DESIGN_REQUEST = "DESIGN_REQUEST"
    MODIFICATION = "MODIFICATION"
    PRICING_INQUIRY = "PRICING_INQUIRY"
    PRODUCT_INQUIRY = "PRODUCT_INQUIRY"
    COMPLAINT = "COMPLAINT"
    SMALL_TALK = "SMALL_TALK"
    EXIT = "EXIT"
    HELP_REQUEST = "HELP_REQUEST"

class DesignComplexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

KERALA_THEMES = {
    "theyyam": "Ancient ritualistic Kerala art form with geometric patterns",
    "kathakali": "Classical Kerala dance with elaborate makeup and costumes",
    "backwaters": "Kerala's famous serene water channels and houseboat cruises",
    "coconut_palms": "Iconic tall coconut trees of Kerala landscape",
    "monsoon": "Heavy seasonal rains that define Kerala's geography",
    "fishing": "Traditional fishing boats and fishing practices",
    "spices": "Cardamom, pepper, cinnamon native to Kerala",
    "temples": "Ancient Hindu temples with ornate architecture",
    "beach": "Sandy beaches along Arabian Sea",
    "boat_race": "Vallam Kali - traditional snake boat races"
}

BOBB_BRAND_TOKENS = {
    "colors": {
        "void_black": "#0A0A0A",
        "signal_gold": "#E8C547",
        "bone": "#FAF7F0",
        "charcoal": "#1E1E1E"
    },
    "tone": "human, calm, intentional, craft-focused",
    "avoid_words": ["revolutionary", "cutting-edge", "disruptive", "premium lifestyle"],
    "cultural_sensitivity": ["respect Kerala culture", "avoid stereotypes", "authentic representation"]
}

PRODUCT_CATALOG = {
    "tshirt_premium": {
        "name": "Premium T-Shirt",
        "price": 65000,  # in paise
        "print_area": "10x12 inches",
        "complexity_min": "simple",
        "complexity_max": "complex",
        "design_style_fit": {"illustration": 0.95, "geometric": 0.85, "photo": 0.90},
        "production_time": 7
    },
    "tote_canvas": {
        "name": "Canvas Tote",
        "price": 45000,
        "print_area": "10x10 inches",
        "complexity_min": "simple",
        "complexity_max": "medium",
        "design_style_fit": {"illustration": 0.88, "geometric": 0.92, "photo": 0.75},
        "production_time": 6
    },
    "cap_snapback": {
        "name": "Snapback Cap",
        "price": 45000,
        "print_area": "3.5x2.5 inches (curved)",
        "complexity_min": "simple",
        "complexity_max": "simple",
        "design_style_fit": {"illustration": 0.70, "geometric": 0.80, "photo": 0.60},
        "production_time": 8
    },
    "phone_case": {
        "name": "Phone Case",
        "price": 65000,
        "print_area": "5x8 inches",
        "complexity_min": "medium",
        "complexity_max": "complex",
        "design_style_fit": {"illustration": 0.85, "geometric": 0.80, "photo": 0.95},
        "production_time": 5
    },
    "laptop_skin": {
        "name": "Laptop Skin",
        "price": 90000,
        "print_area": "13x9 inches",
        "complexity_min": "simple",
        "complexity_max": "complex",
        "design_style_fit": {"illustration": 0.90, "geometric": 0.92, "photo": 0.88},
        "production_time": 5
    }
}

# ============================================================================
# BASE AGENT CLASS
# ============================================================================

class Agent(ABC):
    """Base class for all BOBB agents"""
    
    def __init__(self, agent_id: str, version: str = "1.0"):
        self.agent_id = agent_id
        self.version = version
        self.execution_log = []
    
    async def log_execution(self, action: str, data: Dict, execution_time_ms: int):
        """Log agent execution for debugging/analytics"""
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data": data,
            "execution_time_ms": execution_time_ms
        })
    
    def _create_agent_message(self, message_type: str, payload: Dict, state: str = "PROCESSING") -> Dict:
        """Standard message format for inter-agent communication"""
        return {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "message_type": message_type,
            "state": state,
            "payload": payload,
            "version": self.version
        }
    
    @abstractmethod
    async def process(self, input_data: Dict) -> Dict:
        """Process input and return output"""
        pass

# ============================================================================
# 1. CONVERSATION AGENT
# ============================================================================

class ConversationAgent(Agent):
    """
    Responsibilities:
    - Extract customer story from voice/text
    - Classify intent
    - Extract themes, emotions, keywords
    - Determine cultural references
    - Decide if clarification needed
    """
    
    def __init__(self, use_gemini: bool = True, use_local: bool = False):
        super().__init__("conversation_agent_v1")
        self.use_gemini = use_gemini
        self.use_local = use_local
        
        if use_gemini:
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load conversation agent system prompt"""
        return """You are BOBB AI's Conversation Agent. Your role is to:

1. EXTRACT STORY: Understand the customer's story deeply
   - Themes (what topics matter to them)
   - Emotions (how they feel)
   - Keywords (specific words that stand out)
   - Intent (what they want to create)

2. CLASSIFY INTENT: Determine what the customer wants
   - DESIGN_REQUEST: "Make something about..."
   - MODIFICATION: "Change this..."
   - PRICING_INQUIRY: "How much does..."
   - COMPLAINT: "This is wrong..."
   - SMALL_TALK: Casual conversation
   - HELP_REQUEST: "I need help with..."

3. CULTURAL CONTEXT: If they mention Kerala/Kannur, enhance with cultural knowledge
   - Theyyam, Kathakali, backwaters, spices, fishing, monsoon
   - Be respectful and authentic
   - Connect personal story to cultural elements

4. DETERMINE CLARITY: Decide if you need clarification
   - If vague or missing key info, ask max 2 follow-up questions
   - If clear, proceed to design

OUTPUT AS JSON:
{
    "transcript": "exact customer words",
    "intent": "DESIGN_REQUEST|MODIFICATION|...",
    "story": {
        "themes": ["theme1", "theme2"],
        "emotions": ["emotion1"],
        "keywords": ["word1", "word2"],
        "cultural_references": ["theyyam", "backwaters"]
    },
    "design_complexity": "simple|medium|complex",
    "clarity_score": 0.95,
    "needs_clarification": false,
    "clarification_questions": [],
    "confidence": 0.98
}

Remember: Be human. Be curious. Make the customer feel heard."""
    
    async def extract_story(self, transcript: str = "", text: str = "", session_id: str = "") -> Dict:
        """Extract story from customer input (voice transcript or text)"""
        
        input_text = transcript or text
        if not input_text:
            return {"error": "No input provided"}
        
        start_time = datetime.now()
        
        try:
            # Call Gemini to extract story
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Customer said: \"{input_text}\"\n\nExtract the story and classify intent."
                    }
                ]
            )
            
            # Parse response
            response_text = message.content[0].text
            
            # Extract JSON from response
            try:
                story_json = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                story_json = json.loads(json_match.group()) if json_match else self._parse_fallback(response_text)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.log_execution("extract_story", story_json, int(execution_time))
            
            return story_json
        
        except Exception as e:
            logger.error(f"Conversation agent error: {e}")
            return {"error": str(e), "fallback": True}
    
    def _parse_fallback(self, response_text: str) -> Dict:
        """Fallback parsing if JSON extraction fails"""
        return {
            "transcript": response_text,
            "intent": "DESIGN_REQUEST",
            "story": {
                "themes": ["generic"],
                "emotions": [],
                "keywords": response_text.split()[:5],
                "cultural_references": []
            },
            "design_complexity": "medium",
            "clarity_score": 0.5,
            "needs_clarification": True,
            "confidence": 0.6
        }
    
    async def ask_clarification(self, story: Dict, clarification_response: str) -> Dict:
        """Handle clarification responses"""
        
        clarification_prompt = f"""The customer answered clarification about their story:

Original story: {story.get('story', {})}
Clarification answer: {clarification_response}

Integrate this new information and provide updated story extraction."""
        
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            system=self.system_prompt,
            messages=[{"role": "user", "content": clarification_prompt}]
        )
        
        try:
            updated_story = json.loads(message.content[0].text)
            return updated_story
        except:
            return story
    
    async def process(self, input_data: Dict) -> Dict:
        """Process wrapper for agent orchestrator"""
        transcript = input_data.get("transcript", "")
        text = input_data.get("text", "")
        session_id = input_data.get("session_id", "")
        
        story = await self.extract_story(transcript=transcript, text=text, session_id=session_id)
        
        return self._create_agent_message(
            message_type="output",
            payload=story,
            state="STORY_EXTRACTED"
        )

# ============================================================================
# 2. DESIGN AGENT
# ============================================================================

class DesignAgent(Agent):
    """
    Responsibilities:
    - Translate customer story into visual design prompt
    - Incorporate Kerala cultural elements
    - Create mood boards and design variants
    - Handle design refinements
    """
    
    def __init__(self):
        super().__init__("design_agent_v1")
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        return """You are BOBB AI's Design Agent. Your role is to:

1. TRANSLATE STORY TO VISUAL: Convert customer's story into a detailed SDXL image prompt
   - Extract visual elements from story
   - Map emotions to visual style
   - Incorporate cultural references
   - Consider color palette, composition, style

2. CULTURAL AUTHENTICITY: If Kerala elements are present
   - Theyyam-inspired geometric patterns
   - Kathakali colors and motifs
   - Backwater scenery elements
   - Local symbols and traditions
   - ALWAYS: Be respectful, never stereotypical

3. DESIGN VARIANTS: Create 4 different design approaches:
   - Variant 1: Illustration style
   - Variant 2: Geometric/abstract
   - Variant 3: Photorealistic
   - Variant 4: Watercolor/artistic

4. OUTPUT FORMAT:
{
    "design_prompt": "detailed SDXL prompt for main design",
    "mood_board": ["reference image 1", "reference image 2"],
    "design_metadata": {
        "style": "illustration",
        "cultural_authenticity_score": 0.95,
        "print_feasibility": "excellent",
        "color_count": 4,
        "complexity": "medium",
        "estimated_print_time": "2.5"
    },
    "variants": [
        {"style": "illustration", "mood": "nostalgic", "color_palette": ["gold", "navy", "cream"]},
        {"style": "geometric", "mood": "abstract", "color_palette": ["black", "gold", "white"]},
        {"style": "photorealistic", "mood": "realistic", "color_palette": ["natural", "warm"]},
        {"style": "watercolor", "mood": "artistic", "color_palette": ["soft", "pastel"]}
    ],
    "refinement_suggestions": ["Add text", "Make bolder", "Soften colors"]
}

Color guidance for BOBB brand:
- Primary: Void Black (#0A0A0A), Signal Gold (#E8C547)
- Secondary: Bone (#FAF7F0), Charcoal (#1E1E1E)
- SDXL prompt: Include "brand colors: void black, signal gold, off-white" for consistency

Remember: Create designs that feel personal and authentic to the customer's story."""
    
    async def translate_story(self, story: Dict, product_type: str = "tshirt", session_id: str = "") -> str:
        """Translate story to SDXL-compatible design prompt"""
        
        start_time = datetime.now()
        
        # Format story for prompt
        story_context = {
            "themes": ", ".join(story.get("themes", [])),
            "emotions": ", ".join(story.get("emotions", [])),
            "keywords": ", ".join(story.get("keywords", [])),
            "cultural_references": ", ".join(story.get("cultural_references", [])),
            "complexity": story.get("design_complexity", "medium")
        }
        
        prompt = f"""Create a detailed SDXL design prompt for this story:

Customer Themes: {story_context['themes']}
Emotions: {story_context['emotions']}
Keywords: {story_context['keywords']}
Cultural Elements: {story_context['cultural_references']}
Complexity: {story_context['complexity']}
Product: {product_type}

Generate a comprehensive SDXL prompt that:
1. Captures the essence of the story
2. Incorporates cultural elements respectfully
3. Uses BOBB brand colors (void black, signal gold, cream)
4. Is printable on {product_type} (DTF compatible)
5. Has clear, distinct imagery"""
        
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1200,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            design_output = message.content[0].text
            
            # Extract just the prompt portion
            design_prompt = self._extract_design_prompt(design_output)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.log_execution("translate_story", {"product": product_type}, int(execution_time))
            
            return design_prompt
        
        except Exception as e:
            logger.error(f"Design agent error: {e}")
            return self._get_fallback_prompt(story_context)
    
    def _extract_design_prompt(self, response: str) -> str:
        """Extract the clean SDXL prompt from response"""
        # Look for prompt between markers or just use the text
        lines = response.split('\n')
        prompt_lines = [l for l in lines if l.strip() and not l.startswith('#')]
        return ' '.join(prompt_lines[:300])  # Limit to ~300 words for SDXL
    
    def _get_fallback_prompt(self, story_context: Dict) -> str:
        """Generate fallback prompt if API fails"""
        return f"""A minimalist illustration incorporating: {story_context['themes']}. 
Style: {story_context['complexity']}. 
Emotions: {story_context['emotions']}. 
Colors: void black, signal gold, cream. 
Cultural elements: {story_context['cultural_references']}. 
High quality, printable design, DTF compatible, 1024x1024px, 300 DPI."""
    
    async def apply_refinement(self, original_prompt: str, refinement_type: str, refinement_value: str) -> str:
        """Apply refinement to existing design prompt"""
        
        refinement_instructions = {
            "color_scheme": f"Change color scheme to: {refinement_value}",
            "style": f"Change art style to: {refinement_value}",
            "mood": f"Change mood to: {refinement_value}",
            "focus": f"Change composition focus to: {refinement_value}",
            "elements": f"Modification: {refinement_value}",
            "size": f"Change design size/scale to: {refinement_value}"
        }
        
        instruction = refinement_instructions.get(refinement_type, refinement_value)
        
        prompt = f"""Original design prompt:
{original_prompt}

Refinement instruction: {instruction}

Create an updated SDXL prompt that incorporates this refinement while maintaining the core story elements."""
        
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            system="You are refining a design prompt. Keep the essence but apply the refinement.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._extract_design_prompt(message.content[0].text)
    
    async def process(self, input_data: Dict) -> Dict:
        """Process wrapper"""
        story = input_data.get("story", {})
        product_type = input_data.get("product_type", "tshirt")
        
        prompt = await self.translate_story(story, product_type)
        
        return self._create_agent_message(
            message_type="output",
            payload={
                "design_prompt": prompt,
                "variants_requested": 4,
                "style": "multi-variant"
            },
            state="PROMPT_CREATED"
        )

# ============================================================================
# 3. IMAGE GENERATION AGENT
# ============================================================================

class ImageGenerationAgent(Agent):
    """
    Responsibilities:
    - Generate 4 design variants from prompt
    - Handle SDXL/Gemini image generation
    - Cache designs for performance
    - Manage image quality and consistency
    """
    
    def __init__(self, use_comfyui: bool = True, use_gemini: bool = False):
        super().__init__("image_generation_agent_v1")
        self.use_comfyui = use_comfyui
        self.use_gemini = use_gemini
        self.image_cache = {}  # Simple in-memory cache
        
        if use_gemini:
            self.gemini_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif use_comfyui:
            self.comfyui_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
    
    async def generate_variants(self, prompt: str, session_id: str, num_variants: int = 4) -> List[str]:
        """Generate multiple design variants"""
        
        start_time = datetime.now()
        images = []
        
        for variant_idx in range(num_variants):
            # Modify prompt for variant
            variant_prompt = self._modify_prompt_for_variant(prompt, variant_idx)
            
            # Check cache first
            cache_key = f"{session_id}_{variant_idx}_{hash(variant_prompt) % 10000}"
            if cache_key in self.image_cache:
                images.append(self.image_cache[cache_key])
                continue
            
            # Generate image
            if self.use_comfyui:
                image_url = await self._generate_with_comfyui(variant_prompt)
            elif self.use_gemini:
                image_url = await self._generate_with_gemini(variant_prompt)
            else:
                image_url = f"/placeholder/{session_id}/{variant_idx}.png"
            
            images.append(image_url)
            self.image_cache[cache_key] = image_url
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        await self.log_execution("generate_variants", {"num_variants": num_variants}, int(execution_time))
        
        return images
    
    def _modify_prompt_for_variant(self, base_prompt: str, variant_idx: int) -> str:
        """Create variant-specific prompts"""
        variants = [
            f"{base_prompt}. Style: modern illustration, bold colors",
            f"{base_prompt}. Style: geometric and abstract, minimalist",
            f"{base_prompt}. Style: photorealistic, cinematic lighting",
            f"{base_prompt}. Style: watercolor painting, soft and artistic"
        ]
        return variants[variant_idx % 4]
    
    async def _generate_with_comfyui(self, prompt: str) -> str:
        """Generate image using ComfyUI SDXL"""
        
        comfyui_payload = {
            "prompt": {
                "4": {
                    "inputs": {
                        "ckpt_name": "sd_xl_base_1.0.safetensors"
                    },
                    "class_type": "CheckpointLoaderSimple"
                },
                "5": {
                    "inputs": {
                        "width": 1024,
                        "height": 1024,
                        "batch_size": 1
                    },
                    "class_type": "CheckpointLoader"
                },
                "6": {
                    "inputs": {
                        "text": prompt,
                        "clip": ["4", 1]
                    },
                    "class_type": "CLIPTextEncode(Positive)"
                },
                "7": {
                    "inputs": {
                        "text": "blurry, low quality, watermark",
                        "clip": ["4", 1]
                    },
                    "class_type": "CLIPTextEncode(Negative)"
                },
                "3": {
                    "inputs": {
                        "seed": 123456,
                        "steps": 20,
                        "cfg": 7.0,
                        "sampler_name": "euler",
                        "scheduler": "karras",
                        "denoise": 1,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0]
                    },
                    "class_type": "KSampler"
                },
                "8": {
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2]
                    },
                    "class_type": "VAEDecode"
                },
                "9": {
                    "inputs": {
                        "filename_prefix": f"bobb_design_{uuid.uuid4().hex[:8]}",
                        "images": ["8", 0]
                    },
                    "class_type": "SaveImage"
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.comfyui_url}/prompt",
                json=comfyui_payload,
                timeout=60
            )
            result = response.json()
            # Return path to generated image
            return f"/cache/designs/{result.get('outputs', {}).get('filename', 'image.png')}"
        except Exception as e:
            logger.error(f"ComfyUI error: {e}")
            return f"/placeholder/error_{uuid.uuid4().hex[:6]}.png"
    
    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate image using Gemini 2.5 (requires image generation support)"""
        
        # Note: Claude API doesn't support image generation yet
        # This is a placeholder for future Gemini integration
        logger.warning("Gemini image generation not yet available via Claude API")
        return f"/placeholder/gemini_{uuid.uuid4().hex[:6]}.png"
    
    async def generate_single(self, prompt: str, session_id: str) -> str:
        """Generate single refined variant"""
        images = await self.generate_variants(prompt, session_id, num_variants=1)
        return images[0] if images else None
    
    async def process(self, input_data: Dict) -> Dict:
        """Process wrapper"""
        prompt = input_data.get("prompt", "")
        session_id = input_data.get("session_id", "")
        
        images = await self.generate_variants(prompt, session_id, num_variants=4)
        
        return self._create_agent_message(
            message_type="output",
            payload={"images": images, "num_variants": 4},
            state="IMAGES_GENERATED"
        )

# ============================================================================
# 4. PRODUCT RECOMMENDATION AGENT
# ============================================================================

class ProductAgent(Agent):
    """
    Responsibilities:
    - Recommend products based on design
    - Score products by design fit
    - Handle inventory checks
    - Apply business logic (margins, stock)
    """
    
    def __init__(self):
        super().__init__("product_agent_v1")
    
    async def recommend_products(self, design_analysis: Dict, customer_data: Dict = None) -> List[Dict]:
        """Recommend top 3 products for the design"""
        
        customer_data = customer_data or {}
        recommendations = []
        
        for product_id, specs in PRODUCT_CATALOG.items():
            score = self._calculate_product_fit(design_analysis, specs, customer_data)
            
            recommendations.append({
                "product_id": product_id,
                "product_name": specs["name"],
                "price": specs["price"],  # in paise
                "print_area": specs["print_area"],
                "production_time_minutes": specs["production_time"],
                "fit_score": score,
                "rank": 0  # Will be set after sorting
            })
        
        # Sort by fit score
        recommendations.sort(key=lambda x: x["fit_score"], reverse=True)
        
        # Assign ranks
        for idx, rec in enumerate(recommendations):
            rec["rank"] = idx + 1
        
        execution_time = 150
        await self.log_execution("recommend_products", {"count": len(recommendations)}, execution_time)
        
        return recommendations[:3]  # Return top 3
    
    def _calculate_product_fit(self, design_analysis: Dict, specs: Dict, customer_data: Dict) -> float:
        """Calculate fit score for a product"""
        
        score = 0.0
        
        # Factor 1: Design style fit (40%)
        design_style = design_analysis.get("style", "illustration")
        style_fit = specs["design_style_fit"].get(design_style, 0.7)
        score += style_fit * 0.40
        
        # Factor 2: Design complexity (30%)
        complexity = design_analysis.get("complexity", "medium")
        min_complexity = self._complexity_score(specs["complexity_min"])
        max_complexity = self._complexity_score(specs["complexity_max"])
        complexity_score = self._complexity_score(complexity)
        
        if min_complexity <= complexity_score <= max_complexity:
            score += 0.30
        elif complexity_score > max_complexity:
            score += 0.10
        else:
            score += 0.20
        
        # Factor 3: Price fit (15%)
        budget = customer_data.get("estimated_budget", "medium")
        price = specs["price"]
        
        if budget == "low" and price < 50000:
            score += 0.15
        elif budget == "medium" and 40000 < price < 100000:
            score += 0.15
        elif budget == "high":
            score += 0.12
        else:
            score += 0.05
        
        # Factor 4: Inventory (10%)
        in_stock = customer_data.get("product_availability", {}).get(specs["name"], True)
        if in_stock:
            score += 0.10
        else:
            score -= 0.05
        
        # Factor 5: Business margin (5%)
        # Prefer high-margin products
        margin_bonus = 0.05
        score += margin_bonus
        
        return min(1.0, score)
    
    def _complexity_score(self, level: str) -> float:
        """Convert complexity string to numeric score"""
        return {
            "simple": 0.3,
            "medium": 0.6,
            "complex": 0.9
        }.get(level, 0.5)
    
    async def process(self, input_data: Dict) -> Dict:
        """Process wrapper"""
        design_analysis = input_data.get("design_analysis", {})
        customer_data = input_data.get("customer_data", {})
        
        recommendations = await self.recommend_products(design_analysis, customer_data)
        
        return self._create_agent_message(
            message_type="output",
            payload={"recommendations": recommendations},
            state="PRODUCTS_RECOMMENDED"
        )

# ============================================================================
# 5. COMMERCE AGENT
# ============================================================================

class CommerceAgent(Agent):
    """
    Responsibilities:
    - Manage shopping cart
    - Calculate pricing with discounts
    - Process payments
    - Create orders
    - Track inventory
    """
    
    def __init__(self):
        super().__init__("commerce_agent_v1")
    
    async def calculate_pricing(self, items: List[Dict], customer_type: str = "regular") -> Dict:
        """Calculate pricing with discounts"""
        
        subtotal = sum(item["price"] * item["quantity"] for item in items)
        
        # Quantity discounts
        total_qty = sum(item["quantity"] for item in items)
        discount_percent = 0
        discount_type = None
        
        if total_qty >= 5:
            discount_percent = 15
            discount_type = "quantity_bulk"
        elif total_qty >= 3:
            discount_percent = 10
            discount_type = "quantity_3plus"
        elif total_qty >= 2:
            discount_percent = 5
            discount_type = "quantity_2plus"
        
        # Student discount
        if customer_type == "student":
            discount_percent += 5
            discount_type = "student"
        
        discount_amount = int(subtotal * (discount_percent / 100))
        total = subtotal - discount_amount
        
        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "discount_percent": discount_percent,
            "discount_type": discount_type,
            "tax": 0,  # No tax in India for customization
            "total": total,
            "currency": "INR"
        }
    
    async def create_order(self, order_data: Dict) -> Dict:
        """Create an order"""
        
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        
        order = {
            "order_id": order_id,
            "created_at": datetime.now().isoformat(),
            "items": order_data.get("items", []),
            "customer": {
                "name": order_data.get("customer_name"),
                "phone": order_data.get("customer_phone"),
                "email": order_data.get("customer_email"),
                "name_tag": order_data.get("name_tag_text")
            },
            "pricing": order_data.get("pricing", {}),
            "payment": {
                "method": order_data.get("payment_method"),
                "status": "pending"
            },
            "status": "pending_confirmation"
        }
        
        return order
    
    async def process(self, input_data: Dict) -> Dict:
        """Process wrapper"""
        items = input_data.get("items", [])
        customer_type = input_data.get("customer_type", "regular")
        
        pricing = await self.calculate_pricing(items, customer_type)
        
        return self._create_agent_message(
            message_type="output",
            payload={"pricing": pricing},
            state="PRICING_CALCULATED"
        )

# ============================================================================
# 6. PRODUCTION AGENT
# ============================================================================

class ProductionAgent(Agent):
    """
    Responsibilities:
    - Queue orders for production
    - Track production progress
    - Manage printer/press state
    - Generate production jobs
    """
    
    def __init__(self):
        super().__init__("production_agent_v1")
        self.production_queue = []
    
    async def queue_order(self, order_id: str, items: List[Dict]) -> List[Dict]:
        """Queue order for production"""
        
        jobs = []
        
        for item in items:
            job_id = f"job_{uuid.uuid4().hex[:10]}"
            
            job = {
                "job_id": job_id,
                "order_id": order_id,
                "product_id": item.get("product_id"),
                "design_id": item.get("design_id"),
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "stages": {
                    "print": {"status": "queued", "progress": 0},
                    "press": {"status": "queued", "progress": 0},
                    "stitch": {"status": "queued", "progress": 0},
                    "ready": {"status": "queued", "progress": 0}
                },
                "queue_position": len(self.production_queue) + 1
            }
            
            self.production_queue.append(job)
            jobs.append(job)
        
        return jobs
    
    async def get_job_status(self, job_id: str) -> Dict:
        """Get current status of a production job"""
        
        for job in self.production_queue:
            if job["job_id"] == job_id:
                return job
        
        return None
    
    async def process(self, input_data: Dict) -> Dict:
        """Process wrapper"""
        order_id = input_data.get("order_id")
        items = input_data.get("items", [])
        
        jobs = await self.queue_order(order_id, items)
        
        return self._create_agent_message(
            message_type="output",
            payload={"jobs": jobs, "queue_length": len(self.production_queue)},
            state="JOBS_QUEUED"
        )

# ============================================================================
# 7. AGENT ORCHESTRATOR
# ============================================================================

class AgentOrchestrator:
    """
    Coordinates all agents in sequence
    Manages state, context, and workflow
    """
    
    def __init__(self, use_gemini: bool = True):
        self.conversation_agent = ConversationAgent(use_gemini=use_gemini)
        self.design_agent = DesignAgent()
        self.image_agent = ImageGenerationAgent(use_comfyui=True)
        self.product_agent = ProductAgent()
        self.commerce_agent = CommerceAgent()
        self.production_agent = ProductionAgent()
        
        self.session_context = {}  # Store context per session
    
    async def run_full_workflow(self, customer_input: str, session_id: str) -> Dict:
        """
        Run complete workflow from input to order creation
        Steps: Extract Story → Design → Generate Images → Recommend Products → Ready for Checkout
        """
        
        logger.info(f"🚀 Starting workflow for session: {session_id}")
        
        # Initialize session context
        if session_id not in self.session_context:
            self.session_context[session_id] = {
                "story": None,
                "design_prompt": None,
                "design_images": None,
                "selected_product": None,
                "order": None
            }
        
        ctx = self.session_context[session_id]
        
        # STEP 1: Extract story from customer input
        logger.info("Step 1: Extracting story...")
        story_result = await self.conversation_agent.extract_story(
            text=customer_input,
            session_id=session_id
        )
        
        if story_result.get("error"):
            return {"error": story_result["error"]}
        
        ctx["story"] = story_result
        logger.info(f"✓ Story extracted. Intent: {story_result.get('intent')}")
        
        # STEP 2: Translate story to design prompt
        logger.info("Step 2: Translating to design...")
        design_prompt = await self.design_agent.translate_story(
            story=story_result.get("story", {}),
            product_type="tshirt"
        )
        ctx["design_prompt"] = design_prompt
        logger.info(f"✓ Design prompt created")
        
        # STEP 3: Generate 4 design variants
        logger.info("Step 3: Generating design variants...")
        design_images = await self.image_agent.generate_variants(
            prompt=design_prompt,
            session_id=session_id,
            num_variants=4
        )
        ctx["design_images"] = design_images
        logger.info(f"✓ Generated {len(design_images)} design variants")
        
        # STEP 4: Recommend products
        logger.info("Step 4: Recommending products...")
        product_recommendations = await self.product_agent.recommend_products(
            design_analysis={
                "style": "illustration",
                "complexity": story_result.get("design_complexity", "medium")
            }
        )
        logger.info(f"✓ Recommended {len(product_recommendations)} products")
        
        return {
            "session_id": session_id,
            "story": ctx["story"],
            "design_prompt": ctx["design_prompt"],
            "design_images": ctx["design_images"],
            "product_recommendations": product_recommendations,
            "next_step": "customer_selects_design"
        }
    
    async def process_design_selection(self, session_id: str, selected_variant: int, design_id: str):
        """Handle customer's design selection"""
        
        if session_id not in self.session_context:
            return {"error": "Session not found"}
        
        ctx = self.session_context[session_id]
        ctx["selected_design_variant"] = selected_variant
        ctx["design_id"] = design_id
        
        return {"status": "design_locked", "next_step": "refine_or_product_select"}
    
    async def process_product_selection(self, session_id: str, product_selection: Dict):
        """Handle customer's product selection"""
        
        if session_id not in self.session_context:
            return {"error": "Session not found"}
        
        ctx = self.session_context[session_id]
        ctx["selected_product"] = product_selection
        
        # Calculate pricing
        items = [
            {
                "product_id": product_selection["product_id"],
                "price": product_selection["price"],
                "quantity": product_selection.get("quantity", 1),
                "design_id": ctx.get("design_id")
            }
        ]
        
        pricing = await self.commerce_agent.calculate_pricing(items)
        ctx["pricing"] = pricing
        
        return {
            "pricing": pricing,
            "next_step": "checkout"
        }
    
    async def process_checkout(self, session_id: str, checkout_data: Dict):
        """Complete checkout and create order"""
        
        if session_id not in self.session_context:
            return {"error": "Session not found"}
        
        ctx = self.session_context[session_id]
        
        # Create order
        order_data = {
            "items": [{
                "product_id": ctx["selected_product"]["product_id"],
                "design_id": ctx.get("design_id"),
                "quantity": ctx["selected_product"].get("quantity", 1)
            }],
            "customer_name": checkout_data.get("name"),
            "customer_phone": checkout_data.get("phone"),
            "customer_email": checkout_data.get("email"),
            "name_tag_text": checkout_data.get("name_tag"),
            "payment_method": checkout_data.get("payment_method"),
            "pricing": ctx.get("pricing", {})
        }
        
        order = await self.commerce_agent.create_order(order_data)
        ctx["order"] = order
        
        # Queue for production
        production_jobs = await self.production_agent.queue_order(
            order_id=order["order_id"],
            items=order_data["items"]
        )
        
        return {
            "order": order,
            "production_jobs": production_jobs,
            "next_step": "production"
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def main():
        orchestrator = AgentOrchestrator(use_gemini=True)
        
        # Simulate customer input
        customer_input = """I love the beach and I'm from Kannur. 
        I want something that shows my love for my hometown and the ocean. 
        I want it to be nostalgic but also modern."""
        
        # Run full workflow
        result = await orchestrator.run_full_workflow(customer_input, "session_test_123")
        
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())
