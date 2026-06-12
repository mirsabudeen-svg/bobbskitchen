import { useCallback, useEffect, useRef } from 'react';
import { wsUrl } from '../services/api';
import { useSessionStore } from '../store/session';
import {
  GenerationCompleteMessage,
  GenerationStartedMessage,
  RefinementCompleteMessage,
  ServerMessage,
  SessionResumedMessage,
  SessionState,
  StateChangeMessage,
  VariantReadyMessage,
  VariantSelectedMessage,
} from '../types';

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const closedByUserRef = useRef(false);

  const handleMessage = useCallback((msg: ServerMessage) => {
    const store = useSessionStore.getState();

    switch (msg.type) {
      case 'session_resumed': {
        const m = msg as SessionResumedMessage;
        const resumedState = m.state as SessionState;
        // On a genuine reconnect with prior in-progress state, surface the
        // recovery interstitial so the customer (or a new customer at the
        // kiosk) can choose to continue or start fresh.
        const hasProgress =
          m.is_reconnect &&
          resumedState !== SessionState.IDLE &&
          resumedState !== SessionState.GREETING;
        if (hasProgress) {
          store.setPendingReconnect({
            state: resumedState,
            latest_design: m.latest_design,
            recommendations: m.recommendations,
          });
        } else {
          store.setState(resumedState);
          store.setLatestDesign(m.latest_design);
          store.setRecommendations(m.recommendations);
        }
        break;
      }

      case 'state_change': {
        const m = msg as StateChangeMessage;
        store.setState(m.state as SessionState);
        break;
      }

      case 'generation_started': {
        const m = msg as GenerationStartedMessage;
        store.setTotalVariants(m.total_variants);
        store.setGeneratingProgress(0);
        break;
      }

      case 'variant_ready': {
        const m = msg as VariantReadyMessage;
        store.addVariant({
          variant_id: m.variant_id,
          variant_number: m.variant_number,
          style: m.style,
          image_url: m.image_url,
          is_refined: false,
          success: m.success,
        });
        break;
      }

      case 'generation_complete': {
        const _m = msg as GenerationCompleteMessage;
        void _m;
        // HTTP response already populated latestDesign.variants; WS confirms completion.
        break;
      }

      case 'variant_selected': {
        const m = msg as VariantSelectedMessage;
        store.setSelectedVariantId(m.variant_id);
        break;
      }

      case 'refinement_started':
        // No store update needed — spinner state is driven by HTTP call status.
        break;

      case 'refinement_complete': {
        const m = msg as RefinementCompleteMessage;
        // Append the refined variant so it appears in the preview grid.
        // Style is inherited from the parent; image may load async.
        store.addVariant({
          variant_id: m.new_variant_id,
          variant_number: 999, // placeholder until history is re-fetched
          style: 'illustration',
          image_url: null,
          is_refined: true,
        });
        break;
      }

      default:
        break;
    }
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    closedByUserRef.current = false;

    const connect = () => {
      const ws = new WebSocket(wsUrl(`/ws/${sessionId}`));
      wsRef.current = ws;

      ws.onopen = () => {
        attemptRef.current = 0;
        useSessionStore.getState().setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          handleMessage(JSON.parse(event.data as string) as ServerMessage);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        useSessionStore.getState().setWsConnected(false);
        if (closedByUserRef.current) return;
        const delay = Math.min(
          RECONNECT_BASE_MS * 2 ** attemptRef.current,
          RECONNECT_MAX_MS,
        );
        attemptRef.current += 1;
        setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closedByUserRef.current = true;
      wsRef.current?.close();
    };
  }, [sessionId, handleMessage]);

  const send = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { send };
}
