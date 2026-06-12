import { useEffect, useRef } from 'react';
import { wsUrl } from '../services/api';
import type { StaffOrder } from '../types';

/**
 * Opens a dedicated WebSocket connection for the staff dashboard.
 * The staff tablet doesn't have a customer session — it uses a
 * time-stamped pseudo session ID that the backend treats as a new
 * session (returning a greeting snapshot which we ignore). All we
 * care about are `order_update` events broadcast to all connections.
 */
export function useStaffWebSocket(onOrderUpdate: (order: StaffOrder) => void) {
  const callbackRef = useRef(onOrderUpdate);
  callbackRef.current = onOrderUpdate;

  useEffect(() => {
    const sessionId = `staff-${Date.now()}`;
    const url = wsUrl(`/ws/${sessionId}`);
    let ws: WebSocket;
    let pingInterval: ReturnType<typeof setInterval>;
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let alive = true;

    function connect() {
      ws = new WebSocket(url);

      ws.onopen = () => {
        pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25_000);
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data as string) as { type: string; order?: StaffOrder };
          if (msg.type === 'order_update' && msg.order) {
            callbackRef.current(msg.order);
          }
        } catch {
          // ignore malformed
        }
      };

      ws.onclose = () => {
        clearInterval(pingInterval);
        if (alive) {
          reconnectTimeout = setTimeout(connect, 3_000);
        }
      };
    }

    connect();

    return () => {
      alive = false;
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      ws?.close();
    };
  }, []); // stable: connect once per mount
}
