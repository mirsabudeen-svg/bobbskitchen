import { useCallback, useEffect, useRef } from 'react';
import { wsUrl } from '../services/api';
import { useSessionStore } from '../store/session';
import { ServerMessage, SessionResumedMessage, SessionState, StateChangeMessage } from '../types';

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

/**
 * Connects to the backend WebSocket for a session, dispatches server messages
 * into the Zustand store, and reconnects with exponential backoff.
 */
export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const closedByUserRef = useRef(false);

  const handleMessage = useCallback((msg: ServerMessage) => {
    const store = useSessionStore.getState();
    switch (msg.type) {
      case 'session_resumed': {
        const m = msg as SessionResumedMessage;
        store.setState(m.state);
        store.setLatestDesign(m.latest_design);
        store.setRecommendations(m.recommendations);
        break;
      }
      case 'state_change': {
        const m = msg as StateChangeMessage;
        store.setState(m.state as SessionState);
        break;
      }
      default:
        // Other message types handled in later sprints.
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
          handleMessage(JSON.parse(event.data) as ServerMessage);
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
