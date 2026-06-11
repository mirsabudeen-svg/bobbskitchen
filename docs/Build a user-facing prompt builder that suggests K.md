<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Build a user-facing prompt builder that suggests Kerala themes as they type

Perfect! I've created a **fully functional, user-facing Prompt Builder widget** that you can embed on your Bobbs Store website.

## 📥 Download the Widget

| File | Purpose | Download |
| :-- | :-- | :-- |
| **Prompt Builder Widget** | Interactive HTML/JS tool with automatic Kerala theme suggestions | [bobbs_prompt_builder_widget.html](sandbox:output/bobbs_prompt_builder_widget.html) |


***

## 🎯 How the Widget Works (User Flow)

### Step 1: User Selects Product

```
Dropdown: T-Shirt, Keychain, Flip-Flops, Phone Case, etc.
→ Automatically loads product-specific constraints
```


### Step 2: User Types Design Idea

```
Example input: "I want a Kerala heritage T-shirt with traditional patterns"
↓
Widget detects keywords: "Kerala", "heritage", "traditional"
→ Triggers Kerala theme suggestion mode
```


### Step 3: Automatic Theme Suggestions Appear

```
✨ Suggested Kerala Themes (based on T-Shirt + user intent):

┌─────────────────────────────────────────────────────┐
│ Kasavu White-Gold           [90% match]             │
│ Use a Kasavu-inspired color palette with white     │
│ and gold accents, inspired by traditional Kerala   │
│ sarees                                              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Pookalam Patterns           [85% match]             │
│ Incorporate intricate Pookalam flower pattern       │
│ geometry in the design                              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Malayalam Script            [75% match]             │
│ Include elegant Malayalam script text that reads    │
│ 'your text' with traditional calligraphy style     │
└─────────────────────────────────────────────────────┘
```


### Step 4: User Clicks a Theme

```
User clicks "Kasavu White-Gold"
↓
Widget generates complete AI prompt with:
- Base prompt for T-Shirt
- User's original request
- Selected Kerala theme suffix
- Technical constraints (300 DPI, CMYK, 12x16")
```


### Step 5: User Copies Prompt

```
📝 Your Generated Prompt:
Create a unique and creative design for a custom T-shirt...

USER'S REQUEST: "I want a Kerala heritage T-shirt..."

KERALA THEME TO INCORPORATE: Use a Kasavu-inspired color...

TECHNICAL CONSTRAINTS:
- Minimum DPI: 300 DPI
- Print Area: 12x16 inches chest...
- Color Mode: CMYK

[📋 Copy Prompt] [✨ Generate Prompt] [🔄 Reset]
```


***

## 🌟 Key Features

| Feature | Description |
| :-- | :-- |
| **Real-time Suggestions** | Suggestions appear as user types (after 3+ characters) |
| **Probability Badges** | Shows match percentage (e.g., "90% match") for each theme |
| **Smart Detection** | Detects "Kerala", "heritage", "name", "Malayalam" keywords automatically |
| **Product-Specific** | Each product has its own themed suggestions (e.g., Flip-Flops → Pookalam 95%) |
| **Malayalam Input** | Shows text input field when "Malayalam" or "name" is detected |
| **Technical Info Panel** | Shows DPI, print area, color mode automatically for selected product |
| **One-Click Copy** | Copies prompt to clipboard with ✅ confirmation |
| **Mobile Responsive** | Works on phones, tablets, desktops |
| **Zero Backend Required** | Pure HTML/CSS/JS — embed anywhere |


***

## 📋 Embed Instructions

### Option 1: Direct Embed (Same Domain)

```html
<!-- Add this to your Bobbs Store website -->
<iframe src="path/to/bobbs_prompt_builder_widget.html" 
        width="100%" 
        height="900px" 
        style="border: none; border-radius: 12px;">
</iframe>
```


### Option 2: Inline Embed (Copy Paste Code)

```html
<!-- Copy the entire HTML content from bobbs_prompt_builder_widget.html -->
<!-- Paste it into your webpage's <body> -->
```


### Option 3: Modal Popup

```javascript
// Open widget in a modal when user clicks "Create Design"
function openPromptBuilder() {
    const modal = document.createElement('div');
    modal.innerHTML = '<iframe src="bobbs_prompt_builder_widget.html" width="900" height="900"></iframe>';
    modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:white;z-index:9999;';
    document.body.appendChild(modal);
}
```


***

## 🎨 Screenshot Preview

The widget looks like this:

```
┌─────────────────────────────────────────────────────────┐
│  🎨 Bobbs Store Prompt Builder                          │
│  Create perfect AI design prompts with automatic        │
│  Kerala theme suggestions                               │
├─────────────────────────────────────────────────────────┤
│  Select Product: [T-Shirt ▼]                            │
│                                                         │
│  Describe Your Design Idea:                             │
│  [I want a Kerala heritage T-shirt with traditional...]│
│  Tip: Mention "Kerala", "traditional", "heritage"...    │
│                                                         │
│  ✨ Suggested Kerala Themes                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Kasavu White-Gold        [90% match]            │   │
│  │ Use a Kasavu-inspired color palette...          │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Pookalam Patterns          [85% match]          │   │
│  │ Incorporate intricate Pookalam flower...        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  🔧 Technical Requirements                              │
│  • Minimum DPI: 300 DPI                                 │
│  • Print Area: 12x16 inches chest                       │
│  • Color Mode: CMYK                                     │
│                                                         │
│  [✨ Generate Prompt] [📋 Copy Prompt] [🔄 Reset]       │
└─────────────────────────────────────────────────────────┘
```


***

## 🚀 Integration with Your AI Pipeline

After the user copies the prompt:

```javascript
// Your backend receives the generated prompt
const generatedPrompt = `Create a unique and creative design for a custom T-shirt...`;

// Send to your AI image generator (DALL-E, Midjourney, Stable Diffusion)
const aiResponse = await generateImage(generatedPrompt);

// AI returns image → displayed to user → user can customize further
displayImage(aiResponse.imageUrl);
```


***

## 📊 Complete Asset Library (Now 10 Files)

| \# | File | Type | Use Case |
| :-- | :-- | :-- | :-- |
| 1 | `bobbs_store_product_research.csv` | CSV | 10×7 research matrix |
| 2 | `bobbs_minimum_dpi_requirements.png` | Chart | DPI by product |
| 3 | `bobbs_durability_comparison.png` | Chart | Durability scores |
| 4 | `bobbs_product_complexity_radar.png` | Chart | Design complexity |
| 5 | `bobbs_print_method_comparison.png` | Chart | Durability vs cost |
| 6 | `bobbs_kerala_theme_matrix.png` | Chart | Theme suitability |
| 7 | `bobbs_qa_checklist_flowchart.png` | Chart | QA checklist |
| 8 | `bobbs_ai_prompt_templates.json` | JSON | AI backend templates |
| 9 | `bobbs_qa_workflow_logic.json` | JSON | QA blocking rules |
| 10 | **`bobbs_prompt_builder_widget.html`** | **HTML** | **User-facing widget** ⭐ |


***

## 💡 Next Steps

You can now:

1. **Test the widget** by opening `bobbs_prompt_builder_widget.html` in your browser
2. **Embed it** on your Bobbs Store homepage or product pages
3. **Track usage** by adding Google Analytics to the widget
4. **A/B test** different theme ordering to see which converts best

Want me to add **analytics tracking** to the widget (to see which themes users click most), or create a **admin dashboard** to monitor widget usage and popular themes?

