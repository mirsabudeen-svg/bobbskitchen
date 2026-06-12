/** Typed REST client. Base URL always from VITE_API_BASE_URL. */

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

if (!BASE_URL) {
  console.error('VITE_API_BASE_URL is not set — see frontend/.env.example');
}

// ---------------------------------------------------------------------------
// Response shapes
// ---------------------------------------------------------------------------

export interface CreateSessionResponse {
  session_id: string;
  state: string;
  created_at: string;
  ws_path: string;
}

export interface StoryResponse {
  pipeline_run_id: string;
  session_id: string;
  turn_number: number;
  story: {
    themes: string[];
    emotions: string[];
    keywords: string[];
    cultural_refs: string[];
    design_complexity: string;
    intent: string;
    raw_customer_text: string;
    needs_clarification: boolean;
    clarification_questions: string[];
  };
  needs_clarification: boolean;
  clarification_question: string | null;
}

export interface VariantOut {
  variant_id: string;
  variant_number: number;
  style: string;
  image_url: string | null;
  generation_seed: number | null;
  provider_request_id: string | null;
  provider_name: string;
  model_used: string;
  generation_time_ms: number;
  success: boolean;
  error: string | null;
}

export interface GenerateResponse {
  design_id: string;
  pipeline_run_id: string;
  session_id: string;
  variants: VariantOut[];
  partial_failure?: boolean;
  failed_variant_numbers?: number[];
}

export interface DesignStrategyResponse {
  design_id: string;
  pipeline_run_id: string;
  session_id: string;
  strategy: {
    base_story_summary: string;
    variants: Array<{
      style: string;
      prompt: string;
      negative_prompt: string;
      color_palette: string[];
      mood: string;
      width: number;
      height: number;
    }>;
    design_metadata: {
      cultural_authenticity_score: number;
      print_feasibility: string;
      color_count: number;
      complexity: string;
      estimated_print_time_min: number;
      kerala_themes_used: string[];
    };
    is_fallback: boolean;
  };
  primary_kerala_theme: string | null;
  primary_emotion: string | null;
  key_symbols: string[];
  product_suitability: Record<string, number>;
}

export interface SelectResponse {
  design_id: string;
  selected_variant_id: string;
  design_locked: boolean;
}

export interface RefineResponse {
  design_id: string;
  new_variant_id: string;
  variant_number: number;
  style: string | null;
  image_url: string | null;
  generation_seed: number | null;
  refinement_type: string;
  parent_variant_id: string;
  refinements_used: number;
  refinements_remaining: number;
  success: boolean;
  error: string | null;
}

export interface RecommendationResponse {
  design_id: string;
  pipeline_run_id: string;
  recommendations: Array<{
    rank: number;
    product_id: string;
    product_name: string;
    score: number;
    score_breakdown: {
      design_fit: number;
      complexity_match: number;
      inferred_demographics: number;
      budget_fit: number;
      inventory_available: boolean;
    };
    reasons: string[];
    price_paise: number;
    price_rupees: number;
    print_area_width_in: number;
    print_area_height_in: number;
    production_time_minutes: number;
    mockup_hint: {
      suggested_color: string;
      suggested_size: string | null;
      placement: string | null;
    };
    units_available: number;
    low_stock: boolean;
  }>;
  model_used: string;
}

// ---------------------------------------------------------------------------
// HTTP client
// ---------------------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!resp.ok) {
    const body = await resp.text().catch(() => '');
    throw new Error(`API ${resp.status}: ${body || path}`);
  }
  return (await resp.json()) as T;
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export const api = {
  createSession: () =>
    request<CreateSessionResponse>('/sessions', { method: 'POST' }),

  getSession: (id: string) =>
    request<CreateSessionResponse>(`/sessions/${id}`),

  /** Mark a session abandoned (idle timeout). Errors are ignored — the UI
   *  resets regardless; the backend row simply stays un-flagged. */
  abandonSession: async (sessionId: string): Promise<void> => {
    try {
      await request<unknown>(`/sessions/${sessionId}/abandon`, { method: 'POST' });
    } catch {
      // fire-and-forget
    }
  },

  submitStory: (sessionId: string, text: string) =>
    request<StoryResponse>(`/sessions/${sessionId}/story`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  generateDesign: (sessionId: string, story: StoryResponse['story']) =>
    request<DesignStrategyResponse>(`/sessions/${sessionId}/design`, {
      method: 'POST',
      body: JSON.stringify({ story }),
    }),

  generateImages: (sessionId: string, designId: string) =>
    request<GenerateResponse>(`/sessions/${sessionId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ design_id: designId }),
    }),

  selectVariant: (designId: string, variantId: string) =>
    request<SelectResponse>(`/designs/${designId}/select`, {
      method: 'POST',
      body: JSON.stringify({ variant_id: variantId }),
    }),

  refineVariant: (designId: string, variantId: string, refinementType: string) =>
    request<RefineResponse>(`/designs/${designId}/refine`, {
      method: 'POST',
      body: JSON.stringify({ variant_id: variantId, refinement_type: refinementType }),
    }),

  generateRecommendations: (designId: string) =>
    request<RecommendationResponse>(`/designs/${designId}/recommend`, {
      method: 'POST',
    }),
};

export function wsUrl(wsPath: string): string {
  const httpBase = new URL(BASE_URL);
  const proto = httpBase.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${httpBase.host}${wsPath}`;
}
