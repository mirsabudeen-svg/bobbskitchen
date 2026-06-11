<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Use the Kerala matrix to create prompt templates that automatically suggest suitable themes per product

Add QA checklist logic to your approval workflow to block designs missing critical checks

Perfect! I've created **two production-ready JSON files** that integrate the Kerala theme matrix and QA checklist logic directly into your AI design workflow:

## 📥 Downloadable Files

| File | Purpose | Download |
| :-- | :-- | :-- |
| **AI Prompt Templates** | 10 product-specific templates with automatic Kerala theme suggestions | [bobbs_ai_prompt_templates.json](sandbox:output/bobbs_ai_prompt_templates.json) |
| **QA Workflow Logic** | 7-stage QA checklist with automatic blocking rules | [bobbs_qa_workflow_logic.json](sandbox:output/bobbs_qa_workflow_logic.json) |


***

## 🎯 How the AI Prompt Templates Work

### Automatic Theme Selection Example

When a user types: *"I want a T-shirt with Kerala heritage design"*

The AI automatically:

1. **Detects intent:** Keywords = "Kerala", "heritage" → triggers Kerala theme mode
2. **Selects product:** T-shirt → loads T-shirt template
3. **Suggests themes** (by probability):
    - **Kasavu White-Gold** (90% probability) → *"Use a Kasavu-inspired color palette with white and gold accents, inspired by traditional Kerala sarees"*
    - **Pookalam Patterns** (85% probability) → *"Incorporate intricate Pookalam flower pattern geometry"*
    - **Malayalam Script** (75% probability) → *"Include elegant Malayalam script text"*
4. **Adds technical constraints:** `min_dpi: 300`, `print_area: 12x16 inches`, `color_mode: CMYK`
5. **Generates final prompt** for image AI

### Product-Specific Theme Probabilities

| Product | Top Kerala Theme | Probability | Why? |
| :-- | :-- | :-- | :-- |
| **T-Shirt** | Kasavu White-Gold | 90% | Perfect for fabric, traditional colors |
| **Keychain** | Malayalam Script | 95% | Small scale needs text/initial |
| **Flip-Flops** | Pookalam Patterns | 95% | Geometric = flex-resistant |
| **Helmet Sticker** | Snake Boat Motifs | 95% | High visibility + speed lines |
| **Water Bottle** | Backwater Waves | 95% | Refreshing theme + wrap-friendly |
| **Shoes** | Pookalam Patterns | 80% | Avoids flex zone cracking |


***

## 🔒 How the QA Workflow Logic Blocks Bad Designs

### 7-Stage Automatic QA Pipeline

```
Stage 1: Resolution Check (Critical)
  ↓ IF DPI < 300 → AUTO-REJECT + suggest AI upscaling
  ↓
Stage 2: Color Mode Check (Critical)
  ↓ IF RGB + product needs CMYK → AUTO-REJECT + offer conversion
  ↓
Stage 3: Print Area Fit (Critical)
  ↓ IF exceeds 12x16" → AUTO-REJECT + auto-scale suggestion
  ↓
Stage 4: Material Match (Critical)
  ↓ IF rigid ink on flip-flops → AUTO-REJECT + suggest DTF
  ↓
Stage 5: Durability Prediction (High)
  ↓ IF score < 3/5 → WARN user about lifespan
  ↓
Stage 6: Cultural Sensitivity (High)
  ↓ IF Kathakali on flip-flops → AUTO-REJECT + suggest Pookalam
  ↓
Stage 7: Final Approval (Critical)
  ↓ IF not user-confirmed → BLOCK checkout
```


### Real Blocking Examples

| Bad Design | Blocking Rule | Auto-Fix Suggestion |
| :-- | :-- | :-- |
| 72 DPI T-shirt design | `DPI < 300` | "Upload higher res or use AI upscaling (2x)" |
| RGB Phone Case design | `RGB + UV print needs CMYK` | "Auto-convert to CMYK? (color may shift)" |
| Kathakali on Flip-Flops | `Sacred symbol + foot-worn` | "Try Pookalam pattern instead (same Kerala vibe)" |
| Rigid ink on Shoes | `Ink flex < required` | "Switch to DTF ink (flexible for canvas)" |
| Malayalam misspelling | `spellcheck == False` | "Use Malayalam spellcheck tool (link)" |
| Temple on Laptop Skin | `Temple + heat source` | "Use Kerala Map silhouette instead" |


***

## 🚀 Integration Steps for Your AI Pipeline

### Step 1: Load Prompt Templates

```python
import json
with open('bobbs_ai_prompt_templates.json') as f:
    templates = json.load(f)

# Get T-shirt template
tshirt_template = templates['products']['tshirt']
```


### Step 2: Auto-Suggest Themes Based on User Input

```python
def suggest_themes(user_prompt, product_type):
    template = templates['products'][product_type]
    if any(kw in user_prompt.lower() for kw in ['kerala', 'heritage', 'traditional']):
        # Return top 3 themes by probability
        return sorted(template['kerala_theme_suggestions'], 
                     key=lambda x: x['probability'], reverse=True)[:3]
    else:
        # Return 1 random theme
        import random
        return [random.choice(template['kerala_theme_suggestions'])]
```


### Step 3: Run QA Workflow Automatically

```python
def run_qa_workflow(design, product_type, qa_logic):
    stages = qa_logic['workflow_stages']
    for stage in stages:
        for check in stage['checklist_items']:
            if not eval(check['rule']):  # Execute rule
                if check['blocking']:
                    return {"status": "REJECTED", "reason": check['item'], "suggestion": stage['auto_fix_suggestions'][0]}
    return {"status": "APPROVED"}
```


### Step 4: Auto-Reject + Regenerate Loop

```python
while design_status == "REJECTED":
    fix_suggestion = qa_result['suggestion']
    new_prompt = base_prompt + fix_suggestion
    design = ai_generate(new_prompt)
    design_status = run_qa_workflow(design, product_type, qa_logic)
```


***

## 📋 Complete Asset Library (Now 9 Files)

| \# | File Type | Name | Use Case |
| :-- | :-- | :-- | :-- |
| 1 | CSV | `bobbs_store_product_research.csv` | Full 10×7 research matrix |
| 2 | Chart | `bobbs_minimum_dpi_requirements.png` | DPI requirements |
| 3 | Chart | `bobbs_durability_comparison.png` | Durability scores |
| 4 | Chart | `bobbs_product_complexity_radar.png` | Design complexity |
| 5 | Chart | `bobbs_print_method_comparison.png` | Durability vs cost |
| 6 | Chart | `bobbs_kerala_theme_matrix.png` | Theme suitability heatmap |
| 7 | Chart | `bobbs_qa_checklist_flowchart.png` | QA checklist vs mistakes |
| 8 | **JSON** | `bobbs_ai_prompt_templates.json` | **AI prompt templates with themes** ⭐ |
| 9 | **JSON** | `bobbs_qa_workflow_logic.json` | **QA blocking rules** ⭐ |


***

## 💡 Next Steps

You can now:

1. **Import the JSON files** into your AI design backend (Node.js/Python)
2. **Create a Notion template** for your team to track design approvals using the 7-stage checklist
3. **Build a user-facing prompt builder** that suggests Kerala themes as they type
4. **Set up auto-rejection** in your checkout flow for designs failing critical QA checks

Would you like me to create a **Notion template** for your team's design approval workflow, or a **user-facing prompt builder widget** (HTML/JS) that they can embed on your Bobbs Store website?

