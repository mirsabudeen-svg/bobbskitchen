import { useState } from 'react';
import { api } from '../../services/api';
import type { StaffOrder } from '../../types';

interface Props {
  order: StaffOrder;
  queuePosition: number;
  onStatusChange: () => void;
}

const STATUS_ACTIONS: Record<string, Array<{ label: string; next: string; colour: string }>> = {
  pending:    [{ label: 'Start Printing',  next: 'printing',   colour: 'blue'   }],
  printing:   [
    { label: 'Mark Ready',   next: 'ready',      colour: 'green'  },
    { label: 'Mark Failed',  next: 'failed',     colour: 'red'    },
  ],
  reprinting: [
    { label: 'Mark Ready',   next: 'ready',      colour: 'green'  },
    { label: 'Mark Failed',  next: 'failed',     colour: 'red'    },
  ],
  ready:      [{ label: 'Mark Collected', next: 'collected',  colour: 'green'  }],
  failed:     [{ label: 'Reprint',        next: 'reprinting', colour: 'orange' }],
  collected:  [],
};

const STATUS_PILL: Record<string, string> = {
  pending:    'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  printing:   'bg-blue-500/20 text-blue-300 border-blue-500/30',
  ready:      'bg-green-500/20 text-green-300 border-green-500/30',
  collected:  'bg-white/10 text-white/50 border-white/20',
  failed:     'bg-red-500/20 text-red-300 border-red-500/30',
  reprinting: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
};

const BTN_COLOUR: Record<string, string> = {
  blue:   'bg-blue-600 hover:bg-blue-500 text-white',
  green:  'bg-green-700 hover:bg-green-600 text-white',
  red:    'bg-red-700 hover:bg-red-600 text-white',
  orange: 'bg-orange-600 hover:bg-orange-500 text-white',
};

export function StaffOrderCard({ order, queuePosition, onStatusChange }: Props) {
  const [notes, setNotes] = useState('');
  const [statusLoading, setStatusLoading] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);

  const isPaid = order.payment_status === 'paid';
  const actions = STATUS_ACTIONS[order.order_status] ?? [];
  const showNotesInput = ['printing', 'failed', 'reprinting'].includes(order.order_status);

  async function updateStatus(next: string) {
    setStatusLoading(true);
    try {
      await api.updateOrderStatus(order.order_id, next, notes || undefined);
      setNotes('');
      onStatusChange();
    } finally {
      setStatusLoading(false);
    }
  }

  async function recordPayment(method: 'cash' | 'upi') {
    setPaymentLoading(true);
    try {
      await api.recordPayment(order.order_id, method);
      onStatusChange();
    } finally {
      setPaymentLoading(false);
    }
  }

  return (
    <div
      className={[
        'rounded-xl border p-4 mb-3 bg-white/5',
        order.order_status === 'collected' ? 'opacity-60 border-white/10' : 'border-white/15',
      ].join(' ')}
    >
      {/* Header row */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="font-body text-white/40 text-sm w-6 text-center">
          {queuePosition}
        </span>
        <span className="font-display text-bobb-gold font-bold text-xl tracking-wide">
          {order.short_ref ?? '—'}
        </span>
        <span className="font-body text-white font-semibold flex-1 min-w-0 truncate">
          {order.customer_name}
        </span>
        <span
          className={`font-body text-xs px-2 py-0.5 rounded-full border ${STATUS_PILL[order.order_status] ?? 'bg-white/10 text-white/60 border-white/20'}`}
        >
          {order.order_status.toUpperCase()}
        </span>
        <span
          className={`font-body text-xs px-2 py-0.5 rounded-full border ${isPaid ? 'bg-green-500/15 text-green-400 border-green-500/30' : 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30'}`}
        >
          {isPaid ? `PAID · ${order.payment_method?.toUpperCase()}` : 'UNPAID'}
        </span>
        <span className="font-body text-white/30 text-xs">
          {new Date(order.created_at).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>

      {/* Items */}
      {order.items.map((item) => (
        <div key={item.id} className="flex gap-3 items-start mb-3">
          {item.image_url && (
            <img
              src={item.image_url}
              alt="Design"
              className="w-16 h-16 rounded-lg object-cover border border-white/10 flex-shrink-0"
            />
          )}
          <div className="flex-1 min-w-0">
            <p className="font-body text-white text-sm font-semibold">
              {item.product_name}{' '}
              <span className="font-bold text-bobb-gold">·{item.size}·</span>{' '}
              {item.color} · qty {item.quantity}
            </p>
            {(item.print_width_in && item.print_height_in) && (
              <p className="font-body text-white/40 text-xs mt-0.5">
                Print: {item.print_width_in}"×{item.print_height_in}" · {item.print_placement ?? 'center-chest'}
              </p>
            )}
            {item.name_tag_text && (
              <p className="font-body text-bobb-saffron text-xs mt-1 flex items-center gap-1">
                <span>🏷</span>
                <span>Name tag: <strong>{item.name_tag_text}</strong></span>
                <span className="text-white/30 ml-1">☐ stitched</span>
              </p>
            )}
          </div>
          <p className="font-body text-white font-semibold text-sm whitespace-nowrap">
            ₹{((item.unit_price_paise * item.quantity) / 100).toFixed(0)}
          </p>
        </div>
      ))}

      {/* Total */}
      <div className="flex justify-end border-t border-white/10 pt-2 mb-3">
        <span className="font-body text-white/60 text-sm mr-2">Total</span>
        <span className="font-display text-white font-bold">
          ₹{(order.total_paise / 100).toFixed(0)}
        </span>
      </div>

      {/* Payment buttons */}
      {!isPaid && order.order_status !== 'collected' && (
        <div className="flex items-center gap-2 mb-3">
          <span className="font-body text-white/50 text-xs">Payment:</span>
          <button
            className="bg-white/10 hover:bg-white/20 text-white font-body text-sm px-4 py-1.5 rounded-button transition-colors disabled:opacity-40"
            onClick={() => void recordPayment('cash')}
            disabled={paymentLoading}
          >
            Cash
          </button>
          <button
            className="bg-white/10 hover:bg-white/20 text-white font-body text-sm px-4 py-1.5 rounded-button transition-colors disabled:opacity-40"
            onClick={() => void recordPayment('upi')}
            disabled={paymentLoading}
          >
            UPI
          </button>
        </div>
      )}

      {/* Staff notes */}
      {showNotesInput && (
        <input
          className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 font-body text-white text-sm mb-3 outline-none focus:border-bobb-gold/50 placeholder-white/20"
          placeholder="Staff notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      )}

      {/* Existing notes */}
      {order.staff_notes && (
        <p className="font-body text-white/40 text-xs mb-3 italic">Note: {order.staff_notes}</p>
      )}
      {order.reprint_count > 0 && (
        <p className="font-body text-orange-400 text-xs mb-3">⚠ Reprinted {order.reprint_count}×</p>
      )}

      {/* Action buttons */}
      {actions.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {actions.map((action) => {
            const blockedCollect =
              action.next === 'collected' && !isPaid;
            return (
              <button
                key={action.next}
                className={[
                  'font-body text-sm px-4 py-2 rounded-button transition-colors disabled:opacity-40',
                  BTN_COLOUR[action.colour] ?? 'bg-white/10 text-white hover:bg-white/20',
                ].join(' ')}
                onClick={() => void updateStatus(action.next)}
                disabled={statusLoading || blockedCollect}
                title={blockedCollect ? 'Record payment before collecting' : undefined}
              >
                {statusLoading ? '…' : action.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
