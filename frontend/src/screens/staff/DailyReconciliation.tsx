import { useState } from 'react';
import { api } from '../../services/api';
import type { ReconciliationData } from '../../types';

export function DailyReconciliation({ date }: { date: string }) {
  const [data, setData] = useState<ReconciliationData | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  async function fetch_() {
    setLoading(true);
    try {
      const d = await api.getDailyReconciliation(date);
      setData(d);
      setOpen(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative">
      <button
        className="bg-white/10 hover:bg-white/20 text-white font-body text-sm px-3 py-2 rounded transition-colors disabled:opacity-50"
        onClick={() => void fetch_()}
        disabled={loading}
      >
        {loading ? '…' : 'End-of-Day'}
      </button>

      {open && data && (
        <div className="absolute right-0 top-10 z-50 bg-bobb-navy border border-white/20 rounded-lg p-5 w-64 shadow-xl">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-display text-white font-bold">Summary · {date}</h3>
            <button
              onClick={() => setOpen(false)}
              className="text-white/40 hover:text-white text-lg leading-none"
            >
              ×
            </button>
          </div>
          <table className="w-full font-body text-sm">
            <tbody className="divide-y divide-white/10">
              {[
                ['Total orders', data.total_orders],
                ['Paid', data.paid_orders],
                [
                  'Unpaid',
                  <span key="unpaid" className={data.unpaid_orders > 0 ? 'text-yellow-400 font-bold' : 'text-white'}>
                    {data.unpaid_orders}
                  </span>,
                ],
                ['Cash collected', `₹${(data.cash_total_paise / 100).toFixed(0)}`],
                ['UPI collected', `₹${(data.upi_total_paise / 100).toFixed(0)}`],
                [
                  'Grand total',
                  <span key="total" className="text-bobb-gold font-bold">
                    ₹{(data.grand_total_paise / 100).toFixed(0)}
                  </span>,
                ],
                [
                  'Failed prints',
                  <span key="failed" className={data.failed_orders > 0 ? 'text-red-400' : 'text-white'}>
                    {data.failed_orders}
                  </span>,
                ],
                ['Reprints', data.reprinted_orders],
              ].map(([label, value]) => (
                <tr key={String(label)}>
                  <td className="py-1.5 text-white/60">{label}</td>
                  <td className="py-1.5 text-white text-right">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
