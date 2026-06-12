import { useState } from 'react';
import { api } from '../../services/api';
import type { StaffOrder } from '../../types';

interface Props {
  onFound?: (order: StaffOrder) => void;
}

export function RefLookup({ onFound }: Props) {
  const [ref, setRef] = useState('');
  const [result, setResult] = useState<StaffOrder | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  async function lookup() {
    if (!ref.trim()) return;
    setError(false);
    setResult(null);
    setLoading(true);
    try {
      const data = await api.lookupOrderByRef(ref.trim());
      setResult(data.order);
      onFound?.(data.order);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <input
        className="border border-white/20 bg-white/10 text-white rounded px-3 py-2 font-body text-sm w-24 uppercase placeholder-white/30 outline-none focus:border-bobb-gold"
        placeholder="B-014"
        value={ref}
        onChange={(e) => setRef(e.target.value.toUpperCase())}
        onKeyDown={(e) => e.key === 'Enter' && void lookup()}
        maxLength={8}
      />
      <button
        className="bg-white/10 hover:bg-white/20 text-white font-body text-sm px-3 py-2 rounded transition-colors disabled:opacity-50"
        onClick={() => void lookup()}
        disabled={loading}
      >
        {loading ? '…' : 'Find'}
      </button>
      {error && <span className="font-body text-red-400 text-xs">Not found</span>}
      {result && (
        <div className="flex gap-2 items-center font-body text-sm">
          <span className="text-bobb-gold font-bold">{result.short_ref}</span>
          <span className="text-white">{result.customer_name}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColour(result.order_status)}`}>
            {result.order_status}
          </span>
        </div>
      )}
    </div>
  );
}

function statusColour(status: string): string {
  switch (status) {
    case 'pending': return 'bg-yellow-500/20 text-yellow-300';
    case 'printing': return 'bg-blue-500/20 text-blue-300';
    case 'ready': return 'bg-green-500/20 text-green-300';
    case 'collected': return 'bg-white/20 text-white/60';
    case 'failed': return 'bg-red-500/20 text-red-300';
    case 'reprinting': return 'bg-orange-500/20 text-orange-300';
    default: return 'bg-white/10 text-white/60';
  }
}
