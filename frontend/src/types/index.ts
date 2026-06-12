/** TypeScript types mirroring backend Pydantic schemas. */

export enum SessionState {
  IDLE = 'idle',
  GREETING = 'greeting',
  LISTENING = 'listening',
  CLARIFYING = 'clarifying',
  THINKING = 'thinking',
  GENERATING = 'generating',
  PREVIEW = 'preview',
  REFINING = 'refining',
  PRODUCT_SELECTION = 'product_selection',
  CART = 'cart',
  CHECKOUT = 'checkout',
  PRODUCTION = 'production',
  SUCCESS = 'success',
  ERROR = 'error',
  HELP = 'help',
}

export type VariantStyle = 'illustration' | 'geometric' | 'watercolor' | 'minimalist';

export type RefinementType =
  | 'more_minimal'
  | 'more_cultural'
  | 'more_modern'
  | 'more_premium'
  | 'different_colors'
  | 'different_layout';

export interface Story {
  themes: string[];
  emotions: string[];
  keywords: string[];
  cultural_refs: string[];
  design_complexity: string;
  intent: string;
  raw_customer_text: string;
  needs_clarification: boolean;
  clarification_questions?: string[];
}

export interface DesignVariant {
  variant_id: string;
  variant_number: number;
  style: VariantStyle;
  image_url: string | null;
  is_refined?: boolean;
  /** false when generation failed for this variant (fallback, no image) */
  success?: boolean;
}

export interface LatestDesign {
  design_id: string;
  variants: DesignVariant[];
  selected_variant_id: string | null;
  refinements_count: number;
  design_locked: boolean;
}

export interface ScoreBreakdown {
  design_fit: number;
  complexity_match: number;
  inferred_demographics: number;
  budget_fit: number;
  inventory_available: boolean;
}

export interface MockupHint {
  suggested_color: string;
  suggested_size: string | null;
  placement: string | null;
}

export interface ProductRecommendation {
  rank: number;
  product_id: string;
  product_name: string;
  score: number;
  score_breakdown: ScoreBreakdown;
  reasons: string[];
  price_paise: number;
  price_rupees: number;
  print_area_width_in: number;
  print_area_height_in: number;
  production_time_minutes: number;
  mockup_hint: MockupHint;
  units_available: number;
  low_stock: boolean;
}

// ---------------------------------------------------------------------------
// WebSocket server message types
// ---------------------------------------------------------------------------

export interface SessionResumedMessage {
  type: 'session_resumed';
  session_id: string;
  state: SessionState;
  is_reconnect: boolean;
  session: {
    created_at: string;
    duration_seconds: number;
    customer_name: string | null;
  };
  latest_design: LatestDesign | null;
  recommendations: ProductRecommendation[] | null;
  order: unknown | null;
}

export interface StateChangeMessage {
  type: 'state_change';
  state: SessionState;
  prev_state: SessionState;
  timestamp: string;
}

export interface GenerationStartedMessage {
  type: 'generation_started';
  design_id: string;
  total_variants: number;
  timestamp: string;
}

export interface VariantReadyMessage {
  type: 'variant_ready';
  design_id: string;
  variant_number: number;
  variant_id: string;
  style: VariantStyle;
  image_url: string | null;
  success: boolean;
  timestamp: string;
}

export interface GenerationCompleteMessage {
  type: 'generation_complete';
  design_id: string;
  variant_ids: string[];
  timestamp: string;
}

export interface VariantSelectedMessage {
  type: 'variant_selected';
  design_id: string;
  variant_id: string;
  style: string;
}

export interface RefinementStartedMessage {
  type: 'refinement_started';
  design_id: string;
  parent_variant_id: string;
  refinement_type: string;
  timestamp: string;
}

export interface RefinementCompleteMessage {
  type: 'refinement_complete';
  design_id: string;
  new_variant_id: string;
  refinements_remaining: number;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Order types (customer-facing)
// ---------------------------------------------------------------------------

export interface OrderItemResponse {
  id: string;
  design_variant_id: string;
  product_id: string;
  product_name: string;
  size: string | null;
  color: string;
  quantity: number;
  unit_price_paise: number;
  subtotal_paise: number;
  name_tag_text: string | null;
  image_url: string | null;
  print_width_in: number | null;
  print_height_in: number | null;
  print_placement: string | null;
}

export interface OrderResponse {
  order_id: string;
  short_ref: string | null;
  session_id: string;
  order_status: string;
  payment_status: string;
  payment_method: string | null;
  customer_name: string;
  customer_phone: string | null;
  subtotal_paise: number;
  total_paise: number;
  total_rupees: number;
  currency: string;
  staff_notes: string | null;
  reprint_count: number;
  paid_at: string | null;
  created_at: string;
  items?: OrderItemResponse[];
}

// ---------------------------------------------------------------------------
// Staff types
// ---------------------------------------------------------------------------

export type OrderStatus =
  | 'pending'
  | 'printing'
  | 'ready'
  | 'failed'
  | 'reprinting'
  | 'collected';

export interface StaffOrder extends OrderResponse {
  order_status: OrderStatus;
  items: OrderItemResponse[];
}

export interface OrderListResponse {
  orders: StaffOrder[];
  count: number;
  date: string;
}

export interface ReconciliationData {
  date: string;
  total_orders: number;
  paid_orders: number;
  unpaid_orders: number;
  cash_total_paise: number;
  upi_total_paise: number;
  grand_total_paise: number;
  failed_orders: number;
  reprinted_orders: number;
}

// ---------------------------------------------------------------------------
// WebSocket — order update event
// ---------------------------------------------------------------------------

export interface OrderUpdateMessage {
  type: 'order_update';
  order: StaffOrder;
}

export interface PongMessage {
  type: 'pong';
  timestamp: string;
}

export interface ErrorMessage {
  type: 'error';
  code: string;
  message: string;
  recoverable: boolean;
  suggested_action?: string;
}

export type ServerMessage =
  | SessionResumedMessage
  | StateChangeMessage
  | GenerationStartedMessage
  | VariantReadyMessage
  | GenerationCompleteMessage
  | VariantSelectedMessage
  | RefinementStartedMessage
  | RefinementCompleteMessage
  | OrderUpdateMessage
  | PongMessage
  | ErrorMessage
  | { type: string; [key: string]: unknown };
