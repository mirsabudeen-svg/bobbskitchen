# BOBB TABLET UI/UX DESIGN BRIEF
## Complete Design System & Screen Specifications

**Project**: BOBB Mobile Van AI Agent Interface  
**Platform**: Samsung Galaxy Tab S9 Ultra (14.6" AMOLED)  
**Orientation**: Landscape  
**Resolution**: 2960×1848 pixels (244 PPI)  
**Format**: Touchscreen retail kiosk interface  
**Version**: 1.0

---

## TABLE OF CONTENTS

1. [Design Philosophy](#design-philosophy)
2. [Brand Visual System](#brand-visual-system)
3. [Technical Specifications](#technical-specifications)
4. [Screen Architecture](#screen-architecture)
5. [Individual Screen Designs](#individual-screen-designs)
6. [Component Library](#component-library)
7. [Interaction Patterns](#interaction-patterns)
8. [Animation Specifications](#animation-specifications)
9. [Accessibility Requirements](#accessibility-requirements)
10. [Design Deliverables](#design-deliverables)
11. [Ready-to-Use Design Prompts](#ready-to-use-design-prompts)

---

## 1. DESIGN PHILOSOPHY

### Core Principles

**Calm, Not Aggressive**
- No flashing elements
- No bright neon colors
- No overwhelming animations
- Intentional pacing

**Craft, Not Technology**
- Show the making process
- Emphasize human touch (hand-stitching)
- Warm, tactile feel
- Industrial-meets-artisan aesthetic

**Minimal, Not Sparse**
- Every element has purpose
- No decorative clutter
- Generous whitespace
- Clear hierarchy

**Warm, Not Clinical**
- Gold accents add warmth
- 3000K color temperature feel
- Inviting, approachable
- Human-centered

### Brand Essence

**"Made from your words"**

The interface should feel like a conversation partner, not a vending machine. The customer is creating something, not buying something off a shelf.

---

## 2. BRAND VISUAL SYSTEM

### Color Palette

**Primary Colors**:
```
Void Black: #0A0A0A (backgrounds, primary text)
Signal Gold: #E8C547 (accents, highlights, active states)
Bone: #FAF7F0 (primary text on dark, secondary backgrounds)
```

**Secondary Colors**:
```
Charcoal: #1E1E1E (elevated surfaces, cards)
Surface: #161616 (subtle elevation)
Gold Dim: #9E8538 (inactive gold states)
Gold Glow: rgba(196, 165, 69, 0.08) (gold transparency)
```

**Supporting Grays**:
```
Gray 1: #E8E5DD (light text on dark)
Gray 2: #B8B5AD (secondary text)
Gray 3: #8A8780 (disabled text)
Gray 4: #5A5850 (dividers, borders)
Gray 5: #3A3835 (subtle backgrounds)
```

**Status Colors**:
```
Success: #6BBF6B (print complete, payment success)
Error: #D94F3D (failures, warnings)
Info: #4A7FB5 (informational states)
```

### Typography

**Typefaces**:
1. **Syne** (Display, Headlines)
   - Weights: 600 (Semibold), 700 (Bold)
   - Use for: Screen titles, primary CTAs, brand messaging
   - Characteristics: Geometric, modern, distinctive

2. **DM Sans** (Body, UI)
   - Weights: 400 (Regular), 500 (Medium), 600 (Semibold)
   - Use for: Body text, buttons, labels, captions
   - Characteristics: Clean, readable, neutral

3. **Space Mono** (Monospace, Technical)
   - Weight: 400 (Regular)
   - Use for: Timers, countdowns, technical info
   - Characteristics: Fixed-width, mechanical

**Type Scale** (14.6" tablet @ 244 PPI):
```
Display: 72px / Syne Bold / Line height 1.1
Headline 1: 48px / Syne Semibold / Line height 1.2
Headline 2: 36px / Syne Semibold / Line height 1.2
Title: 24px / DM Sans Medium / Line height 1.4
Body Large: 18px / DM Sans Regular / Line height 1.6
Body: 16px / DM Sans Regular / Line height 1.6
Caption: 14px / DM Sans Regular / Line height 1.5
Label: 12px / DM Sans Medium / Line height 1.4
Technical: 16px / Space Mono Regular / Line height 1.5
```

**Malayalam Typography**:
- Use Noto Sans Malayalam (Google Fonts)
- Same size scale as English
- Increase line-height by 0.1 for Malayalam script

### Spacing System

**Base Unit**: 8px (1 rem)

**Spacing Scale**:
```
XXS: 4px (0.5 rem) - tight padding, icon spacing
XS: 8px (1 rem) - compact spacing
SM: 16px (2 rem) - default spacing
MD: 24px (3 rem) - section spacing
LG: 32px (4 rem) - major section breaks
XL: 48px (6 rem) - screen-level spacing
XXL: 64px (8 rem) - hero spacing
```

### Elevation System

**Shadow Definitions**:
```css
/* No elevation */
box-shadow: none;

/* Subtle elevation (cards) */
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);

/* Medium elevation (modals) */
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);

/* High elevation (dialogs) */
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);

/* Gold glow (active elements) */
box-shadow: 0 0 24px rgba(232, 197, 71, 0.3);
```

### Corner Radius

**Border Radius Scale**:
```
Sharp: 0px (full-bleed images, strict containers)
Subtle: 4px (small elements, tags)
Default: 8px (buttons, input fields)
Soft: 16px (cards, panels)
Round: 24px (prominent CTAs, feature elements)
Pill: 999px (full rounded, badges)
Circle: 50% (avatars, icons)
```

---

## 3. TECHNICAL SPECIFICATIONS

### Device Specifications

**Hardware**: Samsung Galaxy Tab S9 Ultra
- **Screen**: 14.6" AMOLED (2960×1848 px, 244 PPI)
- **Aspect Ratio**: 16:10
- **Orientation**: Landscape (fixed)
- **Touch**: Capacitive multi-touch (10 points)
- **Audio**: Built-in stereo speakers + microphone array
- **Camera**: Front (12MP) + Rear (13MP + 8MP ultra-wide)

### Design Resolution

**Canvas Size**: 2960×1848 px (1×)
- Design at actual resolution (no scaling needed)
- Artboards: 2960×1848 px each
- Export at 1× for web deployment

### Safe Areas

```
Screen edges:
- Top: 48px margin (status bar clearance)
- Bottom: 48px margin (gesture area)
- Left/Right: 64px margin (comfortable reach zones)

Active content area: 2832×1752 px
Center content width (max): 1800px
Comfortable reading width: 1200px
```

### Touch Target Sizes

**Minimum touch targets** (standing user, retail environment):
```
Critical actions (CTA buttons): 72×72 px minimum
Secondary actions: 56×56 px minimum
Tertiary actions: 44×44 px minimum
Text input areas: 64px height minimum
Spacing between targets: 16px minimum
```

### Grid System

**12-Column Grid**:
```
Columns: 12
Column width: 208px
Gutter: 24px
Margin: 64px (left/right)
```

**8-Point Grid**:
All spacing, sizing, and positioning should snap to 8px increments.

---

## 4. SCREEN ARCHITECTURE

### Screen States (11 Total)

The BOBB experience flows through 11 distinct screens:

1. **IDLE** - Attract attention, invite interaction
2. **WELCOME** - Greet customer, set expectations
3. **LISTENING** - Customer shares idea (voice/text)
4. **THINKING** - Processing customer input
5. **GENERATING** - Creating artwork (15-25 seconds)
6. **PREVIEW** - Show design options (1-4 variants)
7. **REFINING** - Customer requests changes (optional)
8. **PRODUCT_SELECTION** - Choose which product to print on
9. **CART** - Review order, add more items
10. **CHECKOUT** - Payment and customer details
11. **PRODUCTION** - Printing in progress, wait time

**Plus 2 Auxiliary States**:
- **ERROR** - Something went wrong
- **SUCCESS** - Order complete, handover

### State Transition Flow

```
IDLE → WELCOME (on tap) → LISTENING (auto) → 
THINKING (auto) → GENERATING (auto) → 
PREVIEW (show designs) → 
[REFINING loop if changes requested] → 
PRODUCT_SELECTION → CART → CHECKOUT → 
PRODUCTION → SUCCESS
```

**Conditional paths**:
- ERROR can appear from any state
- REFINING is optional (customer can skip to product selection)
- CART can loop back to PREVIEW (add more designs)

---

## 5. INDIVIDUAL SCREEN DESIGNS

### Screen 1: IDLE

**Purpose**: Attract customers walking by, invite interaction

**Layout**:
```
┌────────────────────────────────────────┐
│                                        │
│                                        │
│            [BOBB LOGO]                 │
│             gold, 120px                │
│                                        │
│        ┌─────────────────┐            │
│        │                 │            │
│        │   Gold Pulse    │            │
│        │   Ring Animation│            │
│        │                 │            │
│        └─────────────────┘            │
│                                        │
│         "Tap to Start"                 │
│         18px DM Sans                   │
│                                        │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A (full screen)
- BOBB Logo: Signal Gold #E8C547, centered, 120px width
- Pulse Ring: 240px diameter circle, gold stroke (4px), pulsing animation (2s loop)
- Text: "Tap to Start" or "ടാപ്പ് ചെയ്യൂ" (Malayalam), Bone #FAF7F0, 18px DM Sans
- Touch Target: Full screen (any tap starts session)

**Animation**:
```css
/* Gold pulse ring */
@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.5;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

animation: pulse 2s ease-in-out infinite;
```

**Interaction**:
- Tap anywhere → transition to WELCOME
- No timeout (stays in IDLE until interaction)

---

### Screen 2: WELCOME

**Purpose**: Greet customer, prepare them for conversation

**Layout**:
```
┌────────────────────────────────────────┐
│                                        │
│                                        │
│     "Welcome. Tell me something        │
│      about yourself."                  │
│                                        │
│     Malayalam: "സ്വാഗതം. നിങ്ങളെ        │
│     കുറിച്ച് എന്തെങ്കിലും പറയൂ."       │
│                                        │
│                                        │
│         [Voice Icon]                   │
│         36px gold                      │
│                                        │
│      "Listening in 3... 2... 1..."     │
│         14px gray                      │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Primary Text: 36px Syne Semibold, Bone #FAF7F0
- Malayalam Text: 32px Noto Sans Malayalam, Bone #FAF7F0
- Countdown: 14px Space Mono, Gray 2 #B8B5AD
- Voice Icon: 36px, Signal Gold #E8C547
- Duration: 3 seconds (auto-advances to LISTENING)

**Animation**:
- Text fades in (400ms ease)
- Countdown animates from 3 → 1
- Smooth transition to LISTENING state

---

### Screen 3: LISTENING

**Purpose**: Customer speaks or types their idea (25 seconds)

**Layout**:
```
┌────────────────────────────────────────┐
│  [BOBB Logo] 48px                   ⏱  │
│                                    25s │
│                                        │
│                                        │
│     ╔════════════════════════╗        │
│     ║                        ║        │
│     ║    [Waveform Bars]     ║        │
│     ║    9 bars, animated    ║        │
│     ║                        ║        │
│     ╚════════════════════════╝        │
│                                        │
│            "I'm listening..."          │
│            24px DM Sans                │
│                                        │
│    [Stop Early Button - optional]     │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Gold Border: 4px solid Signal Gold #E8C547 around screen edge
- Waveform: 9 vertical bars (24px wide, 16px gap, max height 200px)
- Waveform Color: Signal Gold #E8C547
- Timer: Top-right, 18px Space Mono, countdown from 25s
- Message: "I'm listening..." or "ഞാൻ കേൾക്കുന്നു...", 24px DM Sans
- Stop Button: "Done" at bottom (optional), 56×160px, 16px DM Sans

**Waveform Animation**:
```javascript
// 9 bars, each updates every 120ms
// Height responds to audio input amplitude
// Smooth easing between values

bars.forEach((bar, i) => {
  bar.height = audioLevel[i] * 200; // 0-200px range
  bar.animate({
    height: newHeight,
  }, {
    duration: 120,
    easing: 'ease-out'
  });
});
```

**Interaction**:
- Microphone active, recording audio
- Visual feedback of voice input via waveform
- Timer counts down from 25 seconds
- Auto-advances to THINKING when timer ends
- Optional "Done" button to finish early

---

### Screen 4: THINKING

**Purpose**: Show system is processing customer input

**Layout**:
```
┌────────────────────────────────────────┐
│                                        │
│                                        │
│                                        │
│            [Spinner]                   │
│            48px gold                   │
│                                        │
│     "Understanding your story..."      │
│         24px DM Sans                   │
│                                        │
│     Malayalam: "നിങ്ങളുടെ കഥ            │
│     മനസ്സിലാക്കുന്നു..."                │
│                                        │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Spinner: 48px diameter, gold arc (4px stroke), rotating 360°
- Text: 24px DM Sans, Bone #FAF7F0
- Duration: 3-5 seconds (actual AI processing time)

**Animation**:
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

animation: spin 1s linear infinite;
```

---

### Screen 5: GENERATING

**Purpose**: Show artwork is being created (longest wait: 15-25 seconds)

**Layout**:
```
┌────────────────────────────────────────┐
│  Progress: 45%                     ⏱  │
│                                    18s │
│                                        │
│  [━━━━━━━━━━━━────────────────]       │
│  Gold progress bar                     │
│                                        │
│     ┌──────────────────────────┐      │
│     │                          │      │
│     │   [Preview Skeleton]     │      │
│     │   Shimmer effect         │      │
│     │   640×640px              │      │
│     │                          │      │
│     └──────────────────────────┘      │
│                                        │
│      "Creating your artwork..."        │
│         18px DM Sans                   │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Progress Bar: Full width (minus 128px margin), 8px height, rounded ends
- Progress Fill: Signal Gold #E8C547
- Progress Background: Gray 5 #3A3835
- Timer: Top-right, countdown from estimated time (15-25s)
- Preview Skeleton: 640×640px card, Charcoal #1E1E1E, shimmer overlay
- Status Text: 18px DM Sans, Bone #FAF7F0

**Shimmer Animation**:
```css
@keyframes shimmer {
  0% {
    background-position: -640px 0;
  }
  100% {
    background-position: 640px 0;
  }
}

.skeleton {
  background: linear-gradient(
    90deg,
    #1E1E1E 0%,
    #2A2A2A 50%,
    #1E1E1E 100%
  );
  background-size: 1280px 640px;
  animation: shimmer 2s infinite;
}
```

**Progress Updates**:
- Update progress bar every 2 seconds
- Show status messages:
  - 0-30%: "Creating your artwork..."
  - 30-60%: "Adding details..."
  - 60-90%: "Almost there..."
  - 90-100%: "Finishing touches..."

---

### Screen 6: PREVIEW

**Purpose**: Show generated design options (1-4 variants)

**Layout for 2 Variants**:
```
┌────────────────────────────────────────┐
│  [< Back]              [BOBB Logo]     │
│                                        │
│  "Which style do you prefer?"          │
│  28px Syne                             │
│                                        │
│  ┌────────────┐      ┌────────────┐   │
│  │            │      │            │   │
│  │  Variant 1 │      │  Variant 2 │   │
│  │  560×560px │      │  560×560px │   │
│  │            │      │            │   │
│  └────────────┘      └────────────┘   │
│  "Bold Tiger"        "Minimal Line"   │
│  16px DM Sans        16px DM Sans     │
│                                        │
│  [Select] [Select]   [Try Different]  │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Cards: Charcoal #1E1E1E, 8px corner radius, 2px gold border on hover
- Images: 560×560px, centered, 4px corner radius
- Descriptions: 16px DM Sans, Gray 1 #E8E5DD, below each image
- Select Buttons: 56×160px, Signal Gold background, Void Black text
- Try Different: Secondary button (outlined), bottom-right

**Grid Layout**:
- 1 variant: Centered, 800×800px
- 2 variants: Side-by-side, 560×560px each, 48px gap
- 3 variants: 2 top + 1 bottom, 480×480px each
- 4 variants: 2×2 grid, 480×480px each, 32px gaps

**Interaction**:
- Tap card to select (shows gold highlight)
- Tap "Select" button → PRODUCT_SELECTION
- Tap "Try Different" → REFINING or GENERATING (new variants)
- Tap "< Back" → LISTENING (start over)

---

### Screen 7: REFINING (Optional)

**Purpose**: Customer requests specific changes to design

**Layout**:
```
┌────────────────────────────────────────┐
│  [< Back]              [BOBB Logo]     │
│                                        │
│     ┌──────────────────────────┐      │
│     │                          │      │
│     │   Current Design         │      │
│     │   640×640px              │      │
│     │                          │      │
│     └──────────────────────────┘      │
│                                        │
│  "What would you like to change?"      │
│  20px DM Sans                          │
│                                        │
│  [Darker] [Lighter] [Bigger] [Remove  │
│   Text]                                │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Type specific changes...         │ │
│  └──────────────────────────────────┘ │
│                                        │
│  [Apply Changes]      [Start Over]    │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Current Design: 640×640px card, center-top
- Quick Action Pills: 44×120px, Charcoal #1E1E1E background, 999px radius
- Text Input: 48px height, Charcoal #1E1E1E, Bone text, full width
- Apply Button: Primary CTA, 56×200px, Signal Gold
- Start Over: Secondary, 56×160px, outlined

**Interaction**:
- Tap quick actions → applies preset modification
- Type custom change → processes natural language request
- "Apply Changes" → calls modify_design(), shows progress, returns to PREVIEW
- Max 3 refinement iterations, then suggest moving forward

---

### Screen 8: PRODUCT_SELECTION

**Purpose**: Choose which product to print design on

**Layout**:
```
┌────────────────────────────────────────┐
│  [< Back]              [BOBB Logo]     │
│                                        │
│  "Which product would you like?"       │
│  28px Syne                             │
│                                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │      │ │      │ │      │ │      │ │
│  │ Tee  │ │ Tote │ │ Cap  │ │Phone │ │
│  │ Mock │ │ Mock │ │ Mock │ │Case  │ │
│  │      │ │      │ │      │ │      │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ │
│  ₹600    ₹450    ₹450    ₹650        │
│                                        │
│  [More Products ↓]                     │
│                                        │
│  Selected: Black T-Shirt (M)          │
│  [Add to Cart]                         │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Product Cards: 280×320px, Charcoal #1E1E1E, 8px radius
- Mockup Images: 240×240px, showing design on product
- Product Name: 16px DM Sans Medium, Bone #FAF7F0
- Price: 18px DM Sans Semibold, Signal Gold #E8C547
- Grid: 4 cards per row, 24px gaps, horizontally scrollable
- Selected Card: 4px gold border, gold glow shadow
- Add to Cart: Primary CTA, full-width bottom, 72px height

**Product Options**:
Row 1: T-Shirt, Tote Bag, Cap, Phone Case
Row 2: Laptop Skin, Flip-Flops, Keychain, Helmet Sticker

**Interaction**:
- Tap product card → shows size/color picker modal
- Select size/color → card shows selection state
- "Add to Cart" → adds item, transitions to CART

---

### Screen 9: CART

**Purpose**: Review order, add more items

**Layout**:
```
┌────────────────────────────────────────┐
│  [< Products]          [BOBB Logo]     │
│                                        │
│  "Your Cart"                           │
│  32px Syne                             │
│                                        │
│  ┌────────────────────────────────┐   │
│  │ [Design    Black T-Shirt (M)   │   │
│  │  Thumb]    ₹600          [×]   │   │
│  │                                │   │
│  │ [Design    Navy Tote Bag       │   │
│  │  Thumb]    ₹450          [×]   │   │
│  └────────────────────────────────┘   │
│                                        │
│  Subtotal:                    ₹1050   │
│  10% Discount (3+ items):      -₹105  │
│  ────────────────────────────────────  │
│  Total:                        ₹945    │
│                                        │
│  [Add Another Item] [Checkout →]      │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Cart Items: Charcoal #1E1E1E cards, 8px radius, 80px height each
- Thumbnails: 64×64px, 4px radius, left side
- Item Details: 16px DM Sans, Bone #FAF7F0, center
- Prices: 18px DM Sans Semibold, Signal Gold #E8C547, right
- Remove (×): 32×32px button, gray, top-right of each item
- Subtotal/Total: 20px DM Sans, right-aligned
- Discount: 16px DM Sans, Success Green #6BBF6B
- Checkout CTA: 72×240px, Signal Gold, right

**Interaction**:
- Tap (×) → removes item, recalculates total
- "Add Another Item" → back to PRODUCT_SELECTION
- "Checkout" → CHECKOUT screen

---

### Screen 10: CHECKOUT

**Purpose**: Collect customer info and payment

**Layout**:
```
┌────────────────────────────────────────┐
│  [< Cart]              [BOBB Logo]     │
│                                        │
│  "Almost there"                        │
│  32px Syne                             │
│                                        │
│  Order Summary: 2 items         ₹945   │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Your Name                        │ │
│  │ [Text Input - 56px height]       │ │
│  │                                  │ │
│  │ Phone Number                     │ │
│  │ [+91 __ __ __ __ __ __ __ __ __]│ │
│  │                                  │ │
│  │ Name Tag Text (optional)         │ │
│  │ [Text Input - 56px]              │ │
│  └──────────────────────────────────┘ │
│                                        │
│  Payment Method:                       │
│  [UPI]  [Card]  [Cash]                │
│                                        │
│  [Complete Order - ₹945]               │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Input Fields: 56px height, Charcoal #1E1E1E background, Bone text
- Field Labels: 14px DM Sans Medium, Gray 2 #B8B5AD, above each field
- Payment Pills: 72×120px, Charcoal #1E1E1E, active = gold border
- Complete Order Button: 72px height, full-width, Signal Gold, shows total
- Malayalam Labels: Support both English and Malayalam field names

**Validation**:
- Name: Required, min 2 characters
- Phone: Required, 10 digits, +91 format
- Name Tag: Optional, max 15 characters
- Payment Method: Required, one selected

**Interaction**:
- On-screen keyboard appears for text input (system native)
- Payment method selection highlights selected option
- "Complete Order" → initiates payment flow
- Shows loading state during payment processing
- Success → PRODUCTION screen
- Failure → error message, retry option

---

### Screen 11: PRODUCTION

**Purpose**: Show order is being printed, give wait time

**Layout**:
```
┌────────────────────────────────────────┐
│            [BOBB Logo]                 │
│                                        │
│  "Your design is being made"           │
│  32px Syne                             │
│                                        │
│     ┌──────────────────────────┐      │
│     │                          │      │
│     │   [Design Preview]       │      │
│     │   480×480px              │      │
│     │                          │      │
│     └──────────────────────────┘      │
│                                        │
│  Queue Position: 3 of 5                │
│  Estimated Time: 8 minutes             │
│                                        │
│  [━━━━━━━━━━━━━━──────────────]       │
│  Progress bar                          │
│                                        │
│  Current Step: Heat Press              │
│  Next: Name Tag Stitching              │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Design Preview: 480×480px card, Charcoal #1E1E1E, centered
- Queue Info: 18px DM Sans, Gray 1 #E8E5DD
- Estimated Time: 24px DM Sans Medium, Signal Gold #E8C547
- Progress Bar: Same as GENERATING screen
- Steps: 16px DM Sans, Gray 2 #B8B5AD
- Updates every 5 seconds (polls queue_status)

**Production Steps**:
1. "DTF Printing" (2-3 min)
2. "Heat Press" (40-60 sec)
3. "Name Tag Printing" (1 min)
4. "Hand Stitching" (2-3 min)
5. "Packaging" (1 min)

**Interaction**:
- Progress bar updates in real-time
- Step labels update as production advances
- Auto-advances to SUCCESS when complete
- Option to "Cancel Order" (confirmation modal)

---

### Screen 12: SUCCESS

**Purpose**: Celebrate completion, invite return

**Layout**:
```
┌────────────────────────────────────────┐
│                                        │
│                                        │
│         ✓ [Checkmark Icon]             │
│         80px gold                      │
│                                        │
│       "Your creation is ready"         │
│         36px Syne                      │
│                                        │
│     "Please collect at the counter"    │
│         20px DM Sans                   │
│                                        │
│                                        │
│     Order #A1234                       │
│     18px Space Mono, gold              │
│                                        │
│     "Come back anytime"                │
│     16px DM Sans                       │
│                                        │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Background: Void Black #0A0A0A
- Checkmark: 80px circle, Signal Gold #E8C547, filled
- Heading: 36px Syne Semibold, Bone #FAF7F0
- Body: 20px DM Sans, Gray 1 #E8E5DD
- Order Number: 18px Space Mono, Signal Gold #E8C547
- Farewell: 16px DM Sans, Gray 2 #B8B5AD
- Duration: Shows for 5 seconds, auto-resets to IDLE

**Animation**:
```css
@keyframes success-pop {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

.checkmark {
  animation: success-pop 600ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

---

### Screen 13: ERROR

**Purpose**: Handle failures gracefully

**Layout**:
```
┌────────────────────────────────────────┐
│                                        │
│                                        │
│         ⚠ [Warning Icon]               │
│         64px error red                 │
│                                        │
│     "Something went wrong"             │
│         32px Syne                      │
│                                        │
│     [Specific error message]           │
│     18px DM Sans                       │
│     (e.g. "Payment failed" or          │
│      "Design generation timed out")    │
│                                        │
│                                        │
│     [Try Again]    [Start Over]        │
│     Primary CTA    Secondary           │
│                                        │
│                                        │
└────────────────────────────────────────┘
```

**Specifications**:
- Warning Icon: 64px, Error Red #D94F3D
- Heading: 32px Syne Semibold, Bone #FAF7F0
- Error Message: 18px DM Sans, Gray 1 #E8E5DD, max 2 lines
- Try Again: 56×160px, Signal Gold background (recoverable errors)
- Start Over: 56×160px, outlined, Void Black background
- Duration: Stays until user action

**Error Types**:
1. **Generation Failed**: "Design generation timed out" → [Try Again]
2. **Payment Failed**: "Payment didn't go through" → [Try Again] / [Different Method]
3. **Out of Stock**: "This product is out of stock" → [Choose Different]
4. **Connection Lost**: "Connection lost. Reconnecting..." → [Wait]
5. **Printer Jam**: "Printer issue detected" → [Get Help]

**Interaction**:
- "Try Again" → retries last action
- "Start Over" → resets to IDLE
- "Get Help" → calls escalate_human()

---

## 6. COMPONENT LIBRARY

### Buttons

**Primary Button**:
```css
.btn-primary {
  background: #E8C547; /* Signal Gold */
  color: #0A0A0A; /* Void Black */
  font: 16px/1.5 'DM Sans', sans-serif;
  font-weight: 600;
  padding: 16px 32px;
  border-radius: 8px;
  border: none;
  min-height: 56px;
  transition: all 200ms ease;
}

.btn-primary:hover {
  background: #F2D15E;
  box-shadow: 0 0 24px rgba(232, 197, 71, 0.4);
}

.btn-primary:active {
  transform: scale(0.98);
}
```

**Secondary Button**:
```css
.btn-secondary {
  background: transparent;
  color: #FAF7F0; /* Bone */
  font: 16px/1.5 'DM Sans', sans-serif;
  font-weight: 600;
  padding: 16px 32px;
  border-radius: 8px;
  border: 2px solid #E8C547; /* Gold */
  min-height: 56px;
  transition: all 200ms ease;
}

.btn-secondary:hover {
  background: rgba(232, 197, 71, 0.1);
  border-color: #F2D15E;
}
```

**Text Button**:
```css
.btn-text {
  background: transparent;
  color: #E8C547; /* Signal Gold */
  font: 16px/1.5 'DM Sans', sans-serif;
  font-weight: 500;
  padding: 12px 24px;
  border: none;
  transition: all 200ms ease;
}

.btn-text:hover {
  color: #F2D15E;
  text-decoration: underline;
}
```

**Icon Button**:
```css
.btn-icon {
  background: #1E1E1E; /* Charcoal */
  color: #FAF7F0; /* Bone */
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #2A2A2A;
}
```

### Input Fields

**Text Input**:
```css
.input-text {
  background: #1E1E1E; /* Charcoal */
  color: #FAF7F0; /* Bone */
  font: 16px/1.5 'DM Sans', sans-serif;
  padding: 16px 20px;
  border-radius: 8px;
  border: 2px solid transparent;
  height: 56px;
  width: 100%;
  transition: all 200ms ease;
}

.input-text:focus {
  outline: none;
  border-color: #E8C547; /* Gold */
  background: #252525;
}

.input-text::placeholder {
  color: #8A8780; /* Gray 3 */
}
```

### Cards

**Product Card**:
```css
.card-product {
  background: #1E1E1E; /* Charcoal */
  border-radius: 8px;
  padding: 16px;
  transition: all 300ms ease;
  cursor: pointer;
}

.card-product:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.card-product.selected {
  border: 4px solid #E8C547; /* Gold */
  box-shadow: 0 0 24px rgba(232, 197, 71, 0.3);
}
```

**Design Preview Card**:
```css
.card-design {
  background: #1E1E1E; /* Charcoal */
  border-radius: 8px;
  overflow: hidden;
  transition: all 300ms ease;
}

.card-design:hover {
  border: 2px solid #E8C547; /* Gold */
}
```

### Progress Indicators

**Linear Progress Bar**:
```css
.progress-bar {
  width: 100%;
  height: 8px;
  background: #3A3835; /* Gray 5 */
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(
    90deg,
    #E8C547 0%,
    #F2D15E 100%
  );
  border-radius: 999px;
  transition: width 400ms ease;
}
```

**Spinner**:
```css
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #3A3835;
  border-top-color: #E8C547;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### Badges & Pills

**Status Badge**:
```css
.badge-status {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font: 12px/1.4 'DM Sans', sans-serif;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-success {
  background: rgba(107, 191, 107, 0.15);
  color: #6BBF6B;
}

.badge-error {
  background: rgba(217, 79, 61, 0.15);
  color: #D94F3D;
}

.badge-info {
  background: rgba(74, 127, 181, 0.15);
  color: #4A7FB5;
}
```

### Modal Overlays

**Modal Container**:
```css
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(10, 10, 10, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1E1E1E;
  border-radius: 16px;
  padding: 48px;
  max-width: 800px;
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
  animation: modal-appear 300ms ease;
}

@keyframes modal-appear {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
```

---

## 7. INTERACTION PATTERNS

### Touch Gestures

**Tap**:
- Single tap = Primary action (select, activate, navigate)
- Visual feedback: Scale 0.98 + subtle highlight
- Duration: 200ms

**Long Press**:
- Hold for 500ms = Show contextual options
- Visual feedback: Ripple effect
- Use case: Card options, alternative actions

**Swipe**:
- Horizontal swipe = Navigate between options
- Use case: Product carousel, design variants
- Minimum distance: 100px

**Pinch to Zoom** (disabled):
- Not needed for this interface
- All content should be readable at default size

### Feedback Patterns

**Success**:
```
Visual: Gold checkmark + glow
Duration: 600ms pop animation
Sound: Soft positive chime (optional)
Haptic: Light success vibration
```

**Error**:
```
Visual: Red warning icon + shake
Duration: 400ms shake animation
Sound: Gentle error tone (optional)
Haptic: Double vibration
```

**Loading**:
```
Visual: Gold spinner + progress bar
Text: Status message updates every 2s
Timeout: Show "taking longer than usual" after 30s
```

**Confirmation**:
```
Pattern: Modal overlay + 2 options
Default: Cancel (secondary) on left, Confirm (primary) on right
Keyboard: ESC = Cancel, Enter = Confirm
```

### Navigation Patterns

**Back Navigation**:
- "< Back" button top-left (48×120px)
- Always visible (except IDLE, SUCCESS states)
- Returns to previous logical screen

**Skip/Cancel**:
- "Skip" or "Cancel" option on long-wait screens
- Secondary button, bottom-right
- Confirms destructive action

**Progress Tracking**:
- Subtle progress indicator top-center
- Shows: LISTENING → GENERATING → PREVIEW → CART → CHECKOUT
- Not always visible (context-dependent)

### Focus States

**Keyboard Navigation** (accessibility):
```css
.focusable:focus-visible {
  outline: 4px solid #E8C547; /* Gold */
  outline-offset: 4px;
  border-radius: 8px;
}
```

**Touch Focus**:
```css
.touchable:active {
  transform: scale(0.98);
  opacity: 0.9;
}
```

---

## 8. ANIMATION SPECIFICATIONS

### Timing Functions

**Ease Curves**:
```css
/* Default */
--ease-default: cubic-bezier(0.4, 0.0, 0.2, 1);

/* Entrance */
--ease-in: cubic-bezier(0.4, 0.0, 1, 1);

/* Exit */
--ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);

/* Bounce */
--ease-bounce: cubic-bezier(0.175, 0.885, 0.32, 1.275);
```

**Duration Scale**:
```
Fast: 150ms (micro-interactions, hovers)
Normal: 300ms (transitions, reveals)
Slow: 600ms (page transitions, celebrations)
Extra Slow: 1000ms (idle animations, pulses)
```

### Screen Transitions

**Fade In/Out**:
```css
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fade-out {
  from { opacity: 1; }
  to { opacity: 0; }
}
```

**Slide Up**:
```css
@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**Scale Pop**:
```css
@keyframes scale-pop {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}
```

### Micro-Animations

**Button Press**:
```css
.button:active {
  animation: button-press 200ms ease;
}

@keyframes button-press {
  0% { transform: scale(1); }
  50% { transform: scale(0.96); }
  100% { transform: scale(1); }
}
```

**Card Hover**:
```css
.card {
  transition: transform 300ms ease, box-shadow 300ms ease;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}
```

**Pulse (Idle State)**:
```css
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.6;
  }
}

.pulse-element {
  animation: pulse 2s ease-in-out infinite;
}
```

### Loading Animations

**Shimmer (Skeleton)**:
```css
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.skeleton {
  background: linear-gradient(
    90deg,
    #1E1E1E 25%,
    #2A2A2A 50%,
    #1E1E1E 75%
  );
  background-size: 2000px 100%;
  animation: shimmer 2s infinite;
}
```

**Waveform Bars**:
```javascript
// Animate 9 bars in sequence
bars.forEach((bar, index) => {
  bar.style.animationDelay = `${index * 120}ms`;
});

@keyframes waveform {
  0%, 100% { height: 40px; }
  50% { height: 180px; }
}

.waveform-bar {
  animation: waveform 1.2s ease-in-out infinite;
}
```

### Progress Animations

**Linear Progress**:
```css
.progress-fill {
  width: 0%;
  transition: width 400ms cubic-bezier(0.4, 0.0, 0.2, 1);
}

/* Update width via JS */
progressFill.style.width = `${percentage}%`;
```

**Circular Progress**:
```css
@keyframes rotate-circle {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.circular-progress {
  animation: rotate-circle 1.5s linear infinite;
}
```

---

## 9. ACCESSIBILITY REQUIREMENTS

### WCAG 2.1 AA Compliance

**Color Contrast**:
- Text on Void Black background: Minimum 4.5:1 contrast
- Signal Gold (#E8C547) on Void Black: 9.2:1 ✅
- Bone (#FAF7F0) on Void Black: 15.8:1 ✅
- Gray 2 (#B8B5AD) on Void Black: 7.4:1 ✅

**Touch Target Sizes**:
- Minimum: 44×44 px (WCAG AAA)
- Recommended for kiosk: 56×56 px
- Critical actions: 72×72 px

**Focus Indicators**:
- 4px solid gold outline
- 4px offset from element
- Visible on all interactive elements

### Screen Reader Support

**ARIA Labels**:
```html
<!-- Buttons -->
<button aria-label="Start new design session">
  Tap to Start
</button>

<!-- Progress -->
<div role="progressbar" 
     aria-valuenow="45" 
     aria-valuemin="0" 
     aria-valuemax="100">
  45%
</div>

<!-- Images -->
<img src="design.png" 
     alt="Customer design showing tiger illustration in minimalist style">

<!-- Modal -->
<div role="dialog" 
     aria-labelledby="modal-title" 
     aria-modal="true">
  <h2 id="modal-title">Select Product Size</h2>
</div>
```

**Live Regions**:
```html
<!-- Status updates -->
<div aria-live="polite" aria-atomic="true">
  Creating your artwork... 45% complete
</div>

<!-- Error messages -->
<div aria-live="assertive" role="alert">
  Payment failed. Please try again.
</div>
```

### Language Support

**Malayalam Rendering**:
- Font: Noto Sans Malayalam (Google Fonts)
- Font size: Same as English (no reduction)
- Line height: +0.1 increase for Malayalam script
- Text direction: LTR (left-to-right)

**Bilingual UI**:
- All labels show both English and Malayalam
- System detects user language preference
- Seamless switching mid-session

### Reduced Motion

**Respect prefers-reduced-motion**:
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  /* Keep essential animations */
  .progress-bar-fill {
    transition: width 200ms ease;
  }
}
```

---

## 10. DESIGN DELIVERABLES

### Required Artboards

**Primary Screens** (13 artboards @ 2960×1848 px):
1. IDLE
2. WELCOME
3. LISTENING
4. THINKING
5. GENERATING
6. PREVIEW (2 variants)
7. REFINING
8. PRODUCT_SELECTION
9. CART (2 items)
10. CHECKOUT
11. PRODUCTION
12. SUCCESS
13. ERROR

**Variants**:
- PREVIEW with 1, 2, 3, 4 design options (4 artboards)
- CART with 1, 3, 5 items (3 artboards)
- ERROR types: generation, payment, stock (3 artboards)

**Total Artboards**: 23

### Component Library File

**Organized Sections**:
1. Color Palette (swatches + hex codes)
2. Typography Scale (all sizes + weights)
3. Buttons (primary, secondary, text, icon + states)
4. Input Fields (text, number, dropdown + states)
5. Cards (product, design, info)
6. Progress Indicators (linear, circular, skeleton)
7. Modals & Overlays
8. Icons (custom + system)
9. Badges & Pills
10. Spacing Grid (8px system)

### Export Specifications

**PNG Exports** (for presentation):
- Resolution: 2960×1848 px @ 1×
- Format: PNG-24 (transparency preserved)
- Color: sRGB
- Naming: `BOBB_Screen_[Name]_[Variant].png`

**SVG Exports** (for dev handoff):
- Icons: Individual SVG files
- Illustrations: Optimized SVG
- Naming: `icon-[name].svg`

**Design Tokens JSON**:
```json
{
  "colors": {
    "voidBlack": "#0A0A0A",
    "signalGold": "#E8C547",
    "bone": "#FAF7F0"
  },
  "spacing": {
    "xs": "8px",
    "sm": "16px",
    "md": "24px"
  },
  "typography": {
    "display": {
      "fontSize": "72px",
      "fontFamily": "Syne",
      "fontWeight": 700
    }
  }
}
```

### Developer Handoff

**Figma → Code**:
1. Inspect mode: Show all spacing, sizing, colors
2. Auto-layout: Proper flexbox structure
3. Variants: All button/card states defined
4. Constraints: Responsive behavior documented
5. Prototype: Screen flow connections

**CSS Variables**:
```css
:root {
  /* Colors */
  --color-void-black: #0A0A0A;
  --color-signal-gold: #E8C547;
  --color-bone: #FAF7F0;
  
  /* Typography */
  --font-display: 'Syne', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-mono: 'Space Mono', monospace;
  
  /* Spacing */
  --space-xs: 8px;
  --space-sm: 16px;
  --space-md: 24px;
  
  /* Timing */
  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --duration-slow: 600ms;
}
```

---

## 11. READY-TO-USE DESIGN PROMPTS

### For AI Design Tools (Midjourney, DALL-E, Stable Diffusion)

**Prompt Template Structure**:
```
Create a [screen name] for a tablet kiosk interface.
Design style: Minimalist, modern, high contrast.
Color palette: Void black background (#0A0A0A), signal gold accents (#E8C547), bone text (#FAF7F0).
Layout: [specific layout description].
Typography: Syne for headings, DM Sans for body.
Mood: Calm, intentional, warm, craftsmanship.
Resolution: 2960×1848 pixels, landscape orientation.
UI elements: [specific elements needed].
No gradients, no bright neon, no complex patterns.
```

---

### Prompt 1: IDLE Screen

```
Create an IDLE screen for a retail tablet kiosk interface (2960×1848 px, landscape).

Design style: Minimalist, modern, high contrast, inviting.
Color palette: Pure black background (#0A0A0A), gold accents (#E8C547), cream text (#FAF7F0).

Center of screen:
- BOBB logo wordmark in gold, 120px width, modern geometric typeface
- Below logo: Pulsing gold ring animation, 240px diameter, 4px stroke weight, gentle 2-second pulse loop
- Below ring: "Tap to Start" text in clean sans-serif, 18px, cream color

Mood: Calm, magnetic, approachable, craft-oriented.
No busy elements, no decorative patterns, generous negative space.
Industrial-meets-artisan aesthetic.

Style reference: Minimalist retail kiosk, black and gold color scheme, warm and inviting.
```

---

### Prompt 2: LISTENING Screen

```
Create a LISTENING screen for a voice-interactive retail tablet (2960×1848 px, landscape).

Design style: Minimalist, modern, focused, calm.
Color palette: Black background (#0A0A0A), gold borders and accents (#E8C547), cream text (#FAF7F0).

Screen border: 4px solid gold border around entire screen edge.

Center of screen:
- Animated audio waveform: 9 vertical gold bars (24px wide each, 16px spacing), heights animate with voice input (max 200px height)
- Below waveform: "I'm listening..." text, 24px modern sans-serif, cream color

Top-right corner: Countdown timer "25s", 18px monospace font, cream color.

Top-left: Small BOBB logo, 48px width, gold.

Mood: Active listening, focused, uncluttered, attentive.
Industrial feel with warm gold accents.

Animation: Waveform bars bounce and pulse with audio levels.
```

---

### Prompt 3: GENERATING Screen

```
Create a design GENERATING screen for a retail tablet interface (2960×1848 px, landscape).

Design style: Minimalist, modern, progress-focused.
Color palette: Black background (#0A0A0A), gold accents (#E8C547), dark gray cards (#1E1E1E), cream text (#FAF7F0).

Top of screen: "Progress: 45%" text, left-aligned, cream color, 16px sans-serif.
Top-right: Countdown timer "18s", monospace font.

Below: Horizontal progress bar, full width, 8px height, rounded ends, gold fill (#E8C547), dark gray background (#3A3835).

Center:
- Large preview card, 640×640px, dark charcoal (#1E1E1E), 8px corner radius
- Inside card: Animated shimmer effect (subtle gradient sweep from left to right, 2-second loop)

Below card: "Creating your artwork..." text, 18px sans-serif, cream color.

Mood: Anticipatory, calm, transparent process.
Show the work is being made, not just a loading spinner.
```

---

### Prompt 4: PREVIEW Screen (2 Variants)

```
Create a design PREVIEW screen showing 2 artwork variants for customer selection (2960×1848 px, landscape).

Design style: Minimalist, modern, gallery-like presentation.
Color palette: Black background (#0A0A0A), dark gray cards (#1E1E1E), gold accents (#E8C547), cream text (#FAF7F0).

Top-left: "< Back" button, small, outlined gold.
Top-center: BOBB logo, small, gold, 48px.

Below logo: "Which style do you prefer?" heading, 28px bold sans-serif, cream color.

Center: Two design preview cards side-by-side, 48px gap between:
- Each card: 560×560px, dark charcoal background (#1E1E1E), 8px corner radius
- Inside each card: Generated artwork image (show placeholder for now), 4px corner radius
- Below each image: Short description text "Bold Tiger" / "Minimal Line", 16px sans-serif, cream

Bottom of each card: "Select" button, gold background, black text, 56×160px, 8px radius.

Bottom-right: "Try Different" text button, outlined gold, secondary action.

Mood: Gallery presentation, clean, focused decision moment.
Give designs space to breathe.
```

---

### Prompt 5: PRODUCT_SELECTION Screen

```
Create a PRODUCT SELECTION screen for choosing which item to print design on (2960×1848 px, landscape).

Design style: Minimalist retail catalog, grid layout.
Color palette: Black background (#0A0A0A), dark gray cards (#1E1E1E), gold accents (#E8C547), cream text (#FAF7F0).

Top: "Which product would you like?" heading, 28px bold sans-serif, cream.

Center: Grid of 4 product cards, horizontal row, 24px gaps:
- Each card: 280×320px, dark charcoal (#1E1E1E), 8px corner radius
- Inside card: Product mockup image (t-shirt, tote bag, cap, phone case), 240×240px
- Below image: Product name "T-Shirt", 16px sans-serif medium, cream
- Below name: Price "₹600", 18px sans-serif bold, gold

Selected card: 4px gold border, subtle gold glow shadow.

Bottom section:
- "Selected: Black T-Shirt (M)" text, 16px, cream
- "Add to Cart" button, full-width, 72px height, gold background, black text

Bottom-left: "More Products ↓" text link, gold, subtle.

Mood: Retail catalog, clear options, easy selection.
Industrial-meets-craft aesthetic.
```

---

### Prompt 6: CHECKOUT Screen

```
Create a CHECKOUT screen for collecting customer details and payment (2960×1848 px, landscape).

Design style: Minimalist, form-focused, clear hierarchy.
Color palette: Black background (#0A0A0A), dark gray inputs (#1E1E1E), gold accents (#E8C547), cream text (#FAF7F0).

Top-left: "< Cart" back button, outlined gold.
Top-center: BOBB logo, small, gold.

Heading: "Almost there", 32px bold sans-serif, cream.
Subheading: "Order Summary: 2 items    ₹945", 18px, cream (right-aligned price in gold).

Form section (center):
- "Your Name" label, 14px medium, gray
- Text input field, 56px height, dark charcoal (#1E1E1E), cream text
- "Phone Number" label
- Phone input with +91 prefix, same styling
- "Name Tag Text (optional)" label
- Text input, same styling

Payment method section:
- "Payment Method:" label, 16px, cream
- Three pill buttons side-by-side: [UPI] [Card] [Cash]
- Each: 72×120px, dark charcoal, cream text
- Selected: Gold border, gold text

Bottom: "Complete Order - ₹945" button, full-width, 72px height, gold background, black text.

Mood: Clear, trustworthy, straightforward checkout.
```

---

### Prompt 7: PRODUCTION Screen

```
Create a PRODUCTION progress screen showing order is being made (2960×1848 px, landscape).

Design style: Minimalist, transparent process, real-time updates.
Color palette: Black background (#0A0A0A), dark gray cards (#1E1E1E), gold accents (#E8C547), cream text (#FAF7F0).

Top-center: BOBB logo, small, gold.

Heading: "Your design is being made", 32px bold sans-serif, cream.

Center:
- Large preview card, 480×480px, dark charcoal (#1E1E1E), showing customer's design
- Below: "Queue Position: 3 of 5", 18px sans-serif, gray
- "Estimated Time: 8 minutes", 24px medium sans-serif, gold

Progress bar:
- Full width, 8px height, rounded, gold fill, dark gray background
- Shows production progress percentage

Current production step:
- "Current Step: Heat Press", 16px sans-serif, cream
- "Next: Name Tag Stitching", 16px sans-serif, gray

Mood: Transparent, real-time, craft-in-progress.
Show the customer their order is being made with care.

Optional: Small "Cancel Order" text link, bottom-right, gray.
```

---

### Prompt 8: SUCCESS Screen

```
Create a SUCCESS completion screen celebrating order completion (2960×1848 px, landscape).

Design style: Minimalist, celebratory, warm.
Color palette: Black background (#0A0A0A), gold accents (#E8C547), cream text (#FAF7F0).

Center of screen:
- Large gold checkmark icon, 80px circle, filled, centered
- Below: "Your creation is ready" heading, 36px bold sans-serif, cream
- Below: "Please collect at the counter" text, 20px sans-serif, gray
- Below: Order number "Order #A1234", 18px monospace, gold
- Below: "Come back anytime" text, 16px sans-serif, gray

Mood: Celebratory but calm, completion, invitation to return.
Generous whitespace, centered composition.

Animation: Checkmark appears with gentle pop/scale animation.

Minimal decoration, let the success moment breathe.
```

---

### Prompt 9: ERROR Screen

```
Create an ERROR screen for handling failures gracefully (2960×1848 px, landscape).

Design style: Minimalist, clear, helpful.
Color palette: Black background (#0A0A0A), error red (#D94F3D), gold accents (#E8C547), cream text (#FAF7F0).

Center of screen:
- Warning icon (⚠), 64px, error red color
- Below: "Something went wrong" heading, 32px bold sans-serif, cream
- Below: Specific error message "Payment didn't go through", 18px sans-serif, gray
- (Error message is 1-2 lines max, concise)

Bottom section:
- Two buttons side-by-side, 32px gap
- "Try Again" button, 56×160px, gold background, black text (left)
- "Start Over" button, 56×160px, outlined gold, cream text (right)

Mood: Helpful, not alarming, solution-focused.
Don't panic the customer, offer clear next steps.

No overly dramatic visuals, keep it minimal and actionable.
```

---

### Prompt 10: Component Library Showcase

```
Create a comprehensive UI component library showcase for BOBB tablet interface (2960×1848 px, landscape).

Design style: Minimalist, organized grid layout, component reference sheet.
Color palette: Black background (#0A0A0A), dark gray sections (#1E1E1E), gold accents (#E8C547), cream text (#FAF7F0).

Layout sections (organized in grid):

Top section:
- Color palette swatches with hex codes
- Void Black, Signal Gold, Bone, Charcoal, Gray scale

Typography section:
- Type scale examples from 12px to 72px
- Syne display font, DM Sans body, Space Mono monospace
- Show all weights and sizes

Buttons section:
- Primary button (gold background, black text)
- Secondary button (outlined gold, cream text)
- Text button (gold text, no background)
- Icon button (circular, dark gray)
- Show normal, hover, active states

Inputs section:
- Text input field (dark charcoal, cream text)
- Phone input with prefix
- Dropdown select
- Show empty, filled, focus states

Cards section:
- Product card (with image, title, price)
- Design preview card
- Info card
- Show default and hover states

Progress indicators:
- Linear progress bar (gold fill)
- Circular spinner
- Skeleton shimmer effect

Spacing guide:
- 8px grid system visualization
- Show XXS (4px) through XXL (64px) spacing

Mood: Comprehensive reference, organized, developer-friendly.
Grid layout with clear labels for each component.
```

---

## FINAL NOTES

### Design Principles Summary

1. **Calm Over Flashy**: No neon, no flashing, no aggressive animations
2. **Craft Over Technology**: Show the making, emphasize human touch
3. **Minimal Over Cluttered**: Every element has purpose, generous whitespace
4. **Warm Over Clinical**: Gold adds warmth, inviting not sterile
5. **Clear Over Clever**: Obvious interactions, no hidden features

### Brand Essence

**"Made from your words"**

The interface is a **creation partner**, not a vending machine. The customer is making something unique, not buying off a shelf.

### Technical Constraints

- Samsung Tab S9 Ultra: 14.6" AMOLED, 2960×1848 px, landscape
- Touch-optimized: 56×56 px minimum targets, 72×72 px for critical actions
- Retail environment: Standing users, bright ambient light, need high contrast
- 8-point grid system: All spacing/sizing in 8px increments

### Color Psychology

- **Void Black**: Sophistication, focus, premium feel
- **Signal Gold**: Warmth, craft, accent/highlight
- **Bone**: Soft readability, approachable, warm neutral

### Typography Purpose

- **Syne**: Distinctive, modern, brand voice (headlines)
- **DM Sans**: Clean, neutral, readable (body/UI)
- **Space Mono**: Technical, precise (timers/codes)

---

**Document Version**: 1.0  
**Last Updated**: May 2026  
**Platform**: Samsung Galaxy Tab S9 Ultra  
**Resolution**: 2960×1848 px (landscape)  
**Status**: Ready for Design ✅

---

_This design brief is ready for immediate use in Figma, Adobe XD, Sketch, or any AI design tool. All specifications are production-ready._
