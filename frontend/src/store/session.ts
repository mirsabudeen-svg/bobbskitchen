import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../services/api';
import {
  DesignVariant,
  LatestDesign,
  ProductRecommendation,
  SessionState,
  Story,
} from '../types';

interface PendingReconnect {
  state: SessionState;
  latest_design: LatestDesign | null;
  recommendations: ProductRecommendation[] | null;
}

interface SessionStore {
  // Session identity
  sessionId: string | null;
  currentState: SessionState;
  wsConnected: boolean;

  // Story collection
  storyText: string;
  extractedStory: Story | null;

  // Design pipeline
  latestDesign: LatestDesign | null;
  generatingProgress: number; // 0–4 variants received
  totalVariants: number;

  // Recommendations
  recommendations: ProductRecommendation[] | null;

  // Cart
  selectedProductId: string | null;
  selectedProduct: ProductRecommendation | null;

  // UX state
  pipelineError: string | null;
  pendingReconnect: PendingReconnect | null;

  // Actions
  setSessionId: (id: string) => void;
  setState: (state: SessionState) => void;
  setWsConnected: (connected: boolean) => void;
  setStoryText: (text: string) => void;
  setExtractedStory: (story: Story | null) => void;
  setLatestDesign: (design: LatestDesign | null) => void;
  addVariant: (variant: DesignVariant) => void;
  setGeneratingProgress: (n: number) => void;
  setTotalVariants: (n: number) => void;
  setSelectedVariantId: (id: string) => void;
  setRecommendations: (recs: ProductRecommendation[] | null) => void;
  selectProduct: (rec: ProductRecommendation) => void;
  setPipelineError: (msg: string | null) => void;
  setPendingReconnect: (data: PendingReconnect | null) => void;
  applyReconnect: () => void;
  incrementRefinementsCount: () => void;
  reset: () => void;
  abandonAndReset: () => void;
}

const INITIAL = {
  sessionId: null,
  currentState: SessionState.IDLE,
  wsConnected: false,
  storyText: '',
  extractedStory: null,
  latestDesign: null,
  generatingProgress: 0,
  totalVariants: 4,
  recommendations: null,
  selectedProductId: null,
  selectedProduct: null,
  pipelineError: null,
  pendingReconnect: null,
};

export const useSessionStore = create<SessionStore>()(
  persist(
    (set, get) => ({
      ...INITIAL,

  setSessionId: (id) => set({ sessionId: id }),
  setState: (state) => set({ currentState: state }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setStoryText: (text) => set({ storyText: text }),
  setExtractedStory: (story) => set({ extractedStory: story }),

  setLatestDesign: (design) => set({ latestDesign: design }),

  addVariant: (variant) =>
    set((s) => {
      if (!s.latestDesign) return s;
      const exists = s.latestDesign.variants.some(
        (v) => v.variant_id === variant.variant_id,
      );
      if (exists) return s;
      return {
        latestDesign: {
          ...s.latestDesign,
          variants: [...s.latestDesign.variants, variant],
        },
        generatingProgress: s.generatingProgress + 1,
      };
    }),

  setGeneratingProgress: (n) => set({ generatingProgress: n }),
  setTotalVariants: (n) => set({ totalVariants: n }),

  setSelectedVariantId: (id) =>
    set((s) => ({
      latestDesign: s.latestDesign
        ? { ...s.latestDesign, selected_variant_id: id }
        : s.latestDesign,
    })),

  setRecommendations: (recs) => set({ recommendations: recs }),

  selectProduct: (rec) =>
    set({ selectedProductId: rec.product_id, selectedProduct: rec }),

  setPipelineError: (msg) => set({ pipelineError: msg }),

  setPendingReconnect: (data) => set({ pendingReconnect: data }),

  applyReconnect: () => {
    const pr = get().pendingReconnect;
    if (!pr) return;
    set({
      currentState: pr.state,
      latestDesign: pr.latest_design,
      recommendations: pr.recommendations,
      pendingReconnect: null,
    });
  },

  incrementRefinementsCount: () =>
    set((s) => ({
      latestDesign: s.latestDesign
        ? { ...s.latestDesign, refinements_count: (s.latestDesign.refinements_count ?? 0) + 1 }
        : s.latestDesign,
    })),

      // Sprint 6.2 Fix 1: reset must NOT preserve sessionId — a stale sessionId
      // lets the next customer's journey run on the previous customer's session
      // row. Clearing it triggers App.tsx to create a fresh session.
      reset: () => set({ ...INITIAL }),

      // Mark the backend session abandoned (fire-and-forget), then reset locally.
      abandonAndReset: () => {
        const sid = get().sessionId;
        if (sid) void api.abandonSession(sid).catch(() => {});
        set({ ...INITIAL });
      },
    }),
    {
      // Sprint 6.2 Fix 2: persist session identity across browser refreshes so
      // the session_resumed / SessionResumeOverlay recovery flow can engage.
      name: 'bobb-session',
      partialize: (state) => ({
        sessionId: state.sessionId,
        currentState: state.currentState,
        storyText: state.storyText,
      }),
    },
  ),
);
