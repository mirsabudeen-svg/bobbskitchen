import { useCallback, useEffect, useState } from 'react';
import { api } from '../../services/api';
import { useStaffWebSocket } from '../../hooks/useStaffWebSocket';
import type { StaffOrder } from '../../types';
import { StaffOrderCard } from './StaffOrderCard';
import { RefLookup } from './RefLookup';
import { DailyReconciliation } from './DailyReconciliation';

type StatusFilter = 'pending' | 'printing' | 'ready' | 'collected' | 'failed' | 'all';

const TABS: Array<{ label: string; value: StatusFilter }> = [
  { label: 'Pending',   value: 'pending'   },
  { label: 'Printing',  value: 'printing'  },
  { label: 'Ready',     value: 'ready'     },
  { label: 'Failed',    value: 'failed'    },
  { label: 'Collected', value: 'collected' },
  { label: 'All',       value: 'all'       },
];

export function StaffDashboard() {
  const [orders, setOrders] = useState<StaffOrder[]>([]);
  const [filter, setFilter] = useState<StatusFilter>('pending');
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0]);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listOrders({
        date,
        status: filter === 'all' ? undefined : filter,
      });
      setOrders(data.orders);
    } finally {
      setLoading(false);
    }
  }, [filter, date]);

  useEffect(() => {
    void fetchOrders();
  }, [fetchOrders]);

  // Live updates via WebSocket
  useStaffWebSocket((updated: StaffOrder) => {
    setOrders((prev) => {
      const idx = prev.findIndex((o) => o.order_id === updated.order_id);
      if (idx === -1) {
        // New order — add if it matches current filter or filter is 'all'
        if (filter === 'all' || filter === updated.order_status) {
          return [updated, ...prev];
        }
        return prev;
      }
      const next = [...prev];
      if (filter !== 'all' && updated.order_status !== filter) {
        // Status changed away from current filter — remove from view
        next.splice(idx, 1);
      } else {
        next[idx] = updated;
      }
      return next;
    });
  });

  const pendingCount = orders.filter((o) => o.order_status === 'pending').length;
  const printingCount = orders.filter((o) => o.order_status === 'printing').length;
  const readyCount = orders.filter((o) => o.order_status === 'ready').length;

  return (
    <div className="min-h-screen bg-bobb-navy text-white flex flex-col">
      {/* Header */}
      <header className="bg-bobb-navy/95 border-b border-white/10 px-5 py-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="font-body text-bobb-gold text-xs uppercase tracking-widest">BOBB</span>
          <h1 className="font-display text-white text-xl font-bold">Order Queue</h1>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="bg-white/10 border border-white/20 text-white font-body text-sm px-2 py-1 rounded outline-none focus:border-bobb-gold"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {pendingCount > 0 && (
            <span className="bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 font-body text-xs px-2 py-0.5 rounded-full">
              {pendingCount} pending
            </span>
          )}
          {printingCount > 0 && (
            <span className="bg-blue-500/20 text-blue-300 border border-blue-500/30 font-body text-xs px-2 py-0.5 rounded-full">
              {printingCount} printing
            </span>
          )}
          {readyCount > 0 && (
            <span className="bg-green-500/20 text-green-300 border border-green-500/30 font-body text-xs px-2 py-0.5 rounded-full">
              {readyCount} ready
            </span>
          )}
          <RefLookup />
          <DailyReconciliation date={date} />
          <a
            href="/analytics"
            className="bg-white/10 hover:bg-white/20 text-bobb-gold font-body text-sm px-3 py-1.5 rounded transition-colors"
          >
            Analytics
          </a>
          <button
            onClick={() => void fetchOrders()}
            className="bg-white/10 hover:bg-white/20 text-white font-body text-sm px-3 py-1.5 rounded transition-colors"
          >
            ↻
          </button>
        </div>
      </header>

      {/* Filter tabs */}
      <nav className="flex border-b border-white/10 px-4 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={[
              'font-body text-sm px-4 py-3 border-b-2 transition-colors whitespace-nowrap',
              filter === tab.value
                ? 'border-bobb-gold text-bobb-gold'
                : 'border-transparent text-white/50 hover:text-white/80',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Queue */}
      <main className="flex-1 overflow-y-auto px-4 py-4">
        {loading ? (
          <p className="text-white/40 font-body text-sm text-center py-12">Loading…</p>
        ) : orders.length === 0 ? (
          <p className="text-white/30 font-body text-sm text-center py-12">No orders.</p>
        ) : (
          orders.map((order, idx) => (
            <StaffOrderCard
              key={order.order_id}
              order={order}
              queuePosition={idx + 1}
              onStatusChange={() => void fetchOrders()}
            />
          ))
        )}
      </main>
    </div>
  );
}
