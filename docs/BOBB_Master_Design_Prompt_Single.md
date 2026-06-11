# BOBB TABLET UI - MASTER DESIGN PROMPT
## Single Copy-Paste Prompt for AI Design Tools

---

## MASTER PROMPT (Copy Everything Below)

```
Design a complete tablet kiosk interface for BOBB — a Kerala retail AI agent that transforms customer stories into custom-printed artwork.

TECHNICAL SPECS:
- Device: Samsung Galaxy Tab S9 Ultra, 14.6" AMOLED
- Resolution: 2960×1848 pixels, landscape orientation
- Format: Touchscreen retail kiosk (standing users)
- Design at actual resolution (no scaling)

BRAND VISUAL IDENTITY:
Colors:
- Background: Void Black #0A0A0A (pure black, not dark gray)
- Accent: Signal Gold #E8C547 (warm gold, not yellow or orange)
- Text: Bone #FAF7F0 (cream/off-white, not pure white)
- Cards: Charcoal #1E1E1E (dark gray surfaces)
- Secondary text: Gray #B8B5AD

Typography:
- Headlines: Syne Bold/Semibold (geometric, modern, distinctive)
- Body/UI: DM Sans Regular/Medium (clean, neutral, readable)
- Technical: Space Mono Regular (monospace for timers/codes)
- Malayalam: Noto Sans Malayalam (same sizing as English)

Spacing: 8px base grid system (all spacing in 8px increments)
Corner radius: 8px default (buttons, cards), 16px soft (panels)
Touch targets: 56×56px minimum, 72×72px for primary actions

DESIGN PHILOSOPHY:
- Calm, not aggressive (no flashing, no neon, no bright colors)
- Craft, not technology (show the making process, emphasize human touch)
- Minimal, not sparse (every element has purpose, generous whitespace)
- Warm, not clinical (gold adds warmth, inviting not sterile)
- Industrial-meets-artisan aesthetic

MOOD & STYLE:
- Minimalist retail kiosk
- High contrast (black background, gold accents, cream text)
- Intentional, thoughtful, craftsmanship-focused
- Warm and approachable, not corporate or sterile
- Kerala cultural grounding (subtle, not decorative)

VISUAL REFERENCES:
- Apple Store checkout kiosks (minimalist, premium)
- High-end coffee shop ordering screens (warm, inviting)
- Industrial workshop aesthetic (craft, making visible)
- Modern art gallery walls (negative space, focus)

AVOID:
- No gradients (except subtle shimmer effects for loading)
- No bright neon colors or aggressive pops
- No decorative patterns or busy backgrounds
- No cluttered layouts or overwhelming information
- No generic "tech startup" aesthetics
- No rounded bubbly styles (stay angular and intentional)

11 SCREEN STATES TO DESIGN:

1. IDLE SCREEN - Attract attention
   - Center: BOBB logo (gold, 120px wide)
   - Pulsing gold ring below logo (240px diameter, 4px stroke, 2s pulse loop)
   - "Tap to Start" text (18px, cream)
   - Pure black background, magnetic and inviting

2. WELCOME SCREEN - Greet customer
   - "Welcome. Tell me something about yourself." (36px, cream)
   - Malayalam translation below (32px)
   - Voice icon (36px gold) centered
   - Countdown "Listening in 3... 2... 1..." (14px gray, monospace)

3. LISTENING SCREEN - Recording voice (25s)
   - 4px gold border around entire screen edge
   - Center: 9 animated waveform bars (24px wide each, 16px gaps, max 200px height)
   - Bars animate with voice input (gold color)
   - "I'm listening..." text below (24px)
   - Timer top-right "25s" countdown (18px monospace)
   - Small BOBB logo top-left (48px)

4. THINKING SCREEN - Processing input
   - Center: Gold spinner (48px, rotating)
   - "Understanding your story..." (24px cream)
   - Malayalam translation below
   - Black background, minimal and calm

5. GENERATING SCREEN - Creating artwork (15-25s)
   - Top: "Progress: 45%" (16px cream)
   - Progress bar: full width, 8px height, gold fill, dark gray background
   - Center: 640×640px card (dark charcoal #1E1E1E)
   - Inside card: Animated shimmer effect (gradient sweep, 2s loop)
   - "Creating your artwork..." text below (18px)
   - Timer top-right counting down

6. PREVIEW SCREEN - Show 2-4 design variants
   - "Which style do you prefer?" heading (28px bold)
   - 2 design cards side-by-side: 560×560px each, 48px gap
   - Each card: dark charcoal background, artwork inside, 4px corner radius
   - Description below each: "Bold Tiger" / "Minimal Line" (16px)
   - Gold "Select" button below each (56×160px)
   - "Try Different" secondary button bottom-right (outlined gold)
   - "< Back" button top-left

7. REFINING SCREEN - Make changes (optional)
   - Current design: 640×640px card, center-top
   - "What would you like to change?" (20px)
   - Quick action pills: [Darker] [Lighter] [Bigger] [Remove Text]
   - Each pill: 44×120px, dark gray, rounded (999px radius)
   - Text input field below: full width, 48px height, dark charcoal
   - "Apply Changes" gold button (56×200px)
   - "Start Over" secondary button (outlined)

8. PRODUCT SELECTION SCREEN - Choose product
   - "Which product would you like?" heading (28px)
   - Grid: 4 product cards, horizontal, 24px gaps
   - Each card: 280×320px, dark charcoal, 8px radius
   - Product mockup image: 240×240px (t-shirt, tote, cap, phone case)
   - Product name: 16px medium
   - Price: 18px bold, gold (₹600, ₹450, etc.)
   - Selected card: 4px gold border, subtle gold glow
   - "Add to Cart" button: full-width, 72px height, gold

9. CART SCREEN - Review order
   - "Your Cart" heading (32px)
   - Item list: Each 80px height card, dark charcoal
   - Left: 64×64px thumbnail, 4px radius
   - Center: Product name and details (16px)
   - Right: Price (18px gold), Remove (×) button
   - Bottom section:
     - Subtotal, discount, total (right-aligned)
     - "Add Another Item" secondary button (left)
     - "Checkout →" primary button (right, 72×240px, gold)

10. CHECKOUT SCREEN - Payment
    - "Almost there" heading (32px)
    - "Order Summary: 2 items    ₹945" (18px, price in gold)
    - Form inputs (each 56px height, dark charcoal):
      - Your Name
      - Phone Number (+91 prefix)
      - Name Tag Text (optional)
    - Labels: 14px medium, gray, above each input
    - "Payment Method:" section:
      - Three pills: [UPI] [Card] [Cash]
      - Each: 72×120px, dark charcoal, selected = gold border
    - "Complete Order - ₹945" button: full-width, 72px, gold

11. PRODUCTION SCREEN - Printing progress
    - "Your design is being made" heading (32px)
    - Design preview: 480×480px card, dark charcoal, center
    - "Queue Position: 3 of 5" (18px gray)
    - "Estimated Time: 8 minutes" (24px gold)
    - Progress bar: gold fill showing production %
    - "Current Step: Heat Press" (16px cream)
    - "Next: Name Tag Stitching" (16px gray)

AUXILIARY SCREENS:

SUCCESS SCREEN - Completion
- Large gold checkmark icon (80px circle, filled)
- "Your creation is ready" (36px bold)
- "Please collect at the counter" (20px gray)
- "Order #A1234" (18px monospace, gold)
- "Come back anytime" (16px gray)
- Centered composition, generous whitespace

ERROR SCREEN - Failure handling
- Warning icon ⚠ (64px, error red #D94F3D)
- "Something went wrong" (32px)
- Specific error message (18px gray, 1-2 lines max)
- "Try Again" button (56×160px, gold)
- "Start Over" button (56×160px, outlined)

COMPONENT LIBRARY:
Include these reusable components:

Buttons:
- Primary: Gold background (#E8C547), black text, 56px height, 8px radius
- Secondary: Outlined gold (2px), cream text, 56px height, 8px radius
- Text: Gold text, no background, underline on hover
- Icon: Circular, 48px, dark gray background

Input Fields:
- Height: 56px
- Background: Dark charcoal (#1E1E1E)
- Text: Cream (#FAF7F0)
- Border: 2px transparent, gold on focus
- Corner radius: 8px

Cards:
- Background: Charcoal (#1E1E1E)
- Corner radius: 8px
- Padding: 16px
- Hover: Slight lift (4px translateY), subtle shadow
- Selected: 4px gold border, gold glow shadow

Progress Indicators:
- Linear bar: 8px height, rounded ends, gold fill
- Circular spinner: 48px, gold arc, rotating
- Skeleton shimmer: Gradient sweep animation, 2s loop

ANIMATIONS:
- Button press: Scale 0.98, 200ms
- Card hover: TranslateY(-4px), 300ms
- Pulse (idle): Scale 1→1.15→1, opacity 1→0.6→1, 2s loop
- Fade in: Opacity 0→1, 300ms
- Slide up: TranslateY(40px)→0, opacity 0→1, 400ms
- Shimmer: Background position sweep, 2s infinite

ACCESSIBILITY:
- Color contrast: WCAG 2.1 AA compliant
  - Gold on black: 9.2:1 ✅
  - Cream on black: 15.8:1 ✅
- Touch targets: 56×56px minimum
- Focus indicators: 4px gold outline, 4px offset
- Screen reader: ARIA labels on all interactive elements
- Malayalam: Full rendering support, same sizing as English

LAYOUT STRUCTURE:
- Safe margins: 64px left/right, 48px top/bottom
- Active content area: 2832×1752px
- 12-column grid (208px columns, 24px gutters)
- All elements snap to 8px grid

DESIGN OUTPUT:
Create high-fidelity mockups showing:
1. All 11 primary screens at 2960×1848px
2. Component library with all button states, inputs, cards
3. Interaction states (default, hover, active, disabled)
4. Animation keyframes for micro-interactions
5. Both English and Malayalam text variants

STYLE: Ultra-minimalist retail kiosk interface, black and gold color scheme, high contrast, industrial-meets-craft aesthetic, warm and inviting, Kerala cultural grounding, premium feel, touchscreen-optimized.

FINAL NOTES:
- This is a production retail kiosk, not a mobile app
- Standing users in bright retail environment (high contrast needed)
- Touch-first interaction (no mouse hover states except for prototyping)
- Malayalam language support is essential (Kerala is in India)
- Every screen should feel intentional, calm, and craft-focused
- Avoid generic "AI tech" aesthetics — this is about making, not automation
```

---

## HOW TO USE THIS PROMPT

### For AI Image Generators (Midjourney, DALL-E, Stable Diffusion):

**Option 1: Generate Individual Screens**
```
[Paste master prompt above] + "Generate Screen 3: LISTENING SCREEN"
```

**Option 2: Generate Component Library**
```
[Paste master prompt above] + "Generate comprehensive component library showcase"
```

**Option 3: Generate Complete Design System**
```
[Paste master prompt above] + "Generate all 11 screens as a design system presentation"
```

### For Human Designers (Figma, Adobe XD, Sketch):

1. Copy the entire master prompt above
2. Save as design brief document
3. Create artboards: 2960×1848px (11 screens + components)
4. Follow color codes, spacing, typography specs exactly
5. Use 8px grid system for all alignment
6. Export at 1× resolution (2960×1848px)

### For Design Conversations:

"I need a tablet kiosk interface designed. Here are the complete specifications:"
[Paste master prompt]

---

## QUICK REFERENCE CHEAT SHEET

**Colors (Hex Codes)**:
- `#0A0A0A` - Void Black (background)
- `#E8C547` - Signal Gold (accents)
- `#FAF7F0` - Bone (text)
- `#1E1E1E` - Charcoal (cards)
- `#B8B5AD` - Gray (secondary text)

**Fonts**:
- Syne (headlines) - Google Fonts
- DM Sans (body) - Google Fonts
- Space Mono (technical) - Google Fonts
- Noto Sans Malayalam (Malayalam) - Google Fonts

**Key Measurements**:
- Canvas: 2960×1848px
- Touch target: 56×56px minimum
- Spacing base: 8px
- Corner radius: 8px default
- Margins: 64px sides, 48px top/bottom

**Button Sizes**:
- Primary CTA: 72px height
- Secondary: 56px height
- Icon: 48×48px
- Pill: 44×120px

---

## EXAMPLE SHORT PROMPTS FOR QUICK GENERATION

### Prompt 1: Just IDLE Screen
```
Create an IDLE screen for a retail tablet kiosk (2960×1848px, landscape).
Pure black background (#0A0A0A). Center: gold BOBB logo (120px), gold pulsing ring below (240px diameter, 4px stroke, 2s pulse animation), "Tap to Start" cream text (18px).
Style: Minimalist, high contrast, warm gold accents, industrial-craft aesthetic. Generous negative space, magnetic and inviting.
```

### Prompt 2: Just LISTENING Screen
```
Create a LISTENING screen for voice input (2960×1848px, landscape).
Black background with 4px gold border around screen edge. Center: 9 animated gold waveform bars (24px wide, 16px gaps, heights animate with voice). "I'm listening..." text below (24px cream). Timer "25s" top-right (18px monospace). Small gold BOBB logo top-left (48px).
Style: Minimalist, focused, active listening, high contrast black and gold.
```

### Prompt 3: Full Design System
```
Create complete BOBB tablet UI design system (2960×1848px artboards).
11 screens: IDLE, WELCOME, LISTENING (voice waveform), THINKING, GENERATING (progress), PREVIEW (design variants), REFINING, PRODUCT SELECTION, CART, CHECKOUT, PRODUCTION.
Color: Black background (#0A0A0A), gold accents (#E8C547), cream text (#FAF7F0).
Style: Ultra-minimalist retail kiosk, industrial-craft aesthetic, warm and intentional.
Typography: Syne (headlines), DM Sans (body), high contrast, 8px grid system.
```

---

**Status**: Ready to paste into any design tool ✅  
**Version**: 1.0  
**Platform**: Samsung Galaxy Tab S9 Ultra  
**Resolution**: 2960×1848px landscape
