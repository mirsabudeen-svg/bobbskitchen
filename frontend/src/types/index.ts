/** TypeScript types mirroring backend Pydantic schemas (database_schema.md). */

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

export interface DesignVariant {
  variant_id: string;
  variant_number: number;
  style: VariantStyle;
  image_url: string | null;
  is_refined?: boolean;
}

export interface LatestDesign {
  design_id: string;
  variants: DesignVariant[];
  selected_variant_id: string | null;
  refinements_count: number;
  design_locked: boolean;
}

export interface ProductRecommendation {
  rank: number;
  product_id: string;
  product_name: string;
  score: number;
  reasons: string[];
  price_paise: number;
  print_area: string;
  production_time_minutes: number;
}

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
  | PongMessage
  | ErrorMessage
  | { type: string; [key: string]: unknown };
