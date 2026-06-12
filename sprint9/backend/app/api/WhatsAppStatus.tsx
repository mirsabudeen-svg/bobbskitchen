/**
 * frontend/src/screens/staff/WhatsAppStatus.tsx
 *
 * Sprint 9 — WhatsApp delivery indicator for the staff order card.
 *
 * Shows:
 *   ✅ Artwork sent   — green, with masked phone number
 *   ⏳ Sending…       — while the order is transitioning to ready
 *   ❌ Send failed    — red, with a retry button
 *   –  No phone       — customer didn't provide a number (edge case)
 *
 * Add <WhatsAppStatus order={order} onRetry={handleRetry} /> to StaffOrderCard.tsx
 * inside the order card, below the items section.
 */

import { useState } from "react";

interface Order {
  id: string;
  short_ref: string;
  order_status: string;
  customer_phone: string | null;
  whatsapp_sent: boolean;
}

interface WhatsAppLog {
  id: string;
  success: boolean;
  language: string;
  message_sid: string | null;
  error: string | null;
  attempted_at: string;
  customer_phone: string; // masked: ******3210
}

interface Props {
  order: Order;
  onRetry?: () => void;
}

export function WhatsAppStatus({ order, onRetry }: Props) {
  const [retrying, setRetrying]   = useState(false);
  const [logs, setLogs]           = useState<WhatsAppLog[] | null>(null);
  const [showLogs, setShowLogs]   = useState(false);

  // Only relevant once order reaches 'ready' or beyond
  if (!["ready", "collected"].includes(order.order_status)) {
    return null;
  }

  // Customer didn't provide a phone number
  if (!order.customer_phone) {
    return (
      <div className="whatsapp-status whatsapp-status--none">
        <span className="wa-icon">📵</span>
        <span className="wa-label">No phone — artwork not sent</span>
      </div>
    );
  }

  const fetchLogs = async () => {
    const r = await fetch(`/api/v1/orders/${order.id}/whatsapp-log`);
    if (r.ok) {
      const data = await r.json();
      setLogs(data.logs);
    }
    setShowLogs(true);
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const r = await fetch(`/api/v1/orders/${order.id}/whatsapp-retry`, {
        method: "POST",
      });
      if (r.ok && onRetry) {
        onRetry(); // refresh the order card
      }
    } finally {
      setRetrying(false);
    }
  };

  if (order.whatsapp_sent) {
    return (
      <div className="whatsapp-status whatsapp-status--sent">
        <span className="wa-icon">✅</span>
        <span className="wa-label">Artwork sent on WhatsApp</span>
        <button
          className="wa-log-toggle"
          onClick={showLogs ? () => setShowLogs(false) : fetchLogs}
        >
          {showLogs ? "Hide" : "Details"}
        </button>
        {showLogs && logs && (
          <div className="wa-log-panel">
            {logs.map((log) => (
              <div key={log.id} className="wa-log-entry">
                <span className="wa-log-time">
                  {new Date(log.attempted_at).toLocaleTimeString("en-IN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className="wa-log-phone">{log.customer_phone}</span>
                <span className={`wa-log-lang lang--${log.language}`}>
                  {log.language === "ml" ? "മലയാളം" : "EN"}
                </span>
                <span className="wa-log-sid">{log.message_sid?.slice(-8)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // whatsapp_sent is false and order is ready — delivery failed
  return (
    <div className="whatsapp-status whatsapp-status--failed">
      <span className="wa-icon">❌</span>
      <span className="wa-label">Artwork not sent</span>
      <button
        className="btn btn--warning wa-retry"
        onClick={handleRetry}
        disabled={retrying}
      >
        {retrying ? "Sending…" : "Retry"}
      </button>
      <button
        className="wa-log-toggle"
        onClick={showLogs ? () => setShowLogs(false) : fetchLogs}
      >
        {showLogs ? "Hide" : "Why?"}
      </button>
      {showLogs && logs && (
        <div className="wa-log-panel wa-log-panel--error">
          {logs.map((log) => (
            <div key={log.id} className="wa-log-entry wa-log-entry--error">
              <span className="wa-log-time">
                {new Date(log.attempted_at).toLocaleTimeString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              <span className="wa-log-error">{log.error}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
