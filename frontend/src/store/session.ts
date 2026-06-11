import { create } from 'zustand';
import {
  LatestDesign,
  ProductRecommendation,
  SessionState,
} from '../types';

interface SessionStore {
  sessionId: string | null;
  currentState: SessionState;
  latestDesign: LatestDesign | null;
  recommendations: ProductRecommendation[] | null;
  wsConnected: boolean;
  setSessionId: (id: string) => void;
  setState: (state: SessionState) => void;
  setLatestDesign: (design: LatestDesign | null) => void;
  setRecommendations: (recs: ProductRecommendation[] | null) => void;
  setWsConnected: (connected: boolean) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessionId: null,
  currentState: SessionState.IDLE,
  latestDesign: null,
  recommendations: null,
  wsConnected: false,
  setSessionId: (id) => set({ sessionId: id }),
  setState: (state) => set({ currentState: state }),
  setLatestDesign: (design) => set({ latestDesign: design }),
  setRecommendations: (recs) => set({ recommendations: recs }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  reset: () =>
    set({
      sessionId: null,
      currentState: SessionState.IDLE,
      latestDesign: null,
      recommendations: null,
    }),
}));
