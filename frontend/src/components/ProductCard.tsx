import { motion } from 'framer-motion';
import { ProductRecommendation } from '../types';

interface ProductCardProps {
  rec: ProductRecommendation;
  selected: boolean;
  onSelect: (rec: ProductRecommendation) => void;
}

const RANK_BADGES = ['Best Match', 'Great Choice', 'Alternative'];

export function ProductCard({ rec, selected, onSelect }: ProductCardProps) {
  const badge = RANK_BADGES[rec.rank - 1] ?? `#${rec.rank}`;
  const scorePct = Math.round(rec.score * 100);

  return (
    <motion.button
      onClick={() => onSelect(rec)}
      whileTap={{ scale: 0.98 }}
      className={[
        'relative flex flex-col rounded-card border-4 p-5 text-left transition-all duration-200 w-full',
        selected
          ? 'border-bobb-gold bg-bobb-gold/5 shadow-lg shadow-bobb-gold/30'
          : 'border-bobb-navy/10 bg-white hover:border-bobb-navy/30',
      ].join(' ')}
    >
      {/* Rank badge */}
      <div className="flex items-center justify-between mb-3">
        <span
          className={[
            'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide',
            rec.rank === 1
              ? 'bg-bobb-gold text-bobb-navy'
              : 'bg-bobb-navy/10 text-bobb-navy',
          ].join(' ')}
        >
          {badge}
        </span>
        {rec.low_stock && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-semibold rounded">
            Low Stock
          </span>
        )}
      </div>

      {/* Product name */}
      <h3 className="font-display text-xl text-bobb-navy font-semibold leading-tight mb-1">
        {rec.product_name}
      </h3>

      {/* Score bar */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex-1 h-1.5 rounded-full bg-bobb-navy/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-bobb-gold"
            initial={{ width: 0 }}
            animate={{ width: `${scorePct}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        <span className="text-xs font-bold text-bobb-navy tabular-nums">{scorePct}%</span>
      </div>

      {/* Reasons */}
      <ul className="space-y-1.5 mb-4 flex-1">
        {rec.reasons.slice(0, 3).map((reason, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-bobb-navy/70">
            <span className="mt-0.5 text-bobb-green flex-shrink-0">✓</span>
            <span>{reason}</span>
          </li>
        ))}
      </ul>

      {/* Price + details */}
      <div className="flex items-end justify-between pt-3 border-t border-bobb-navy/10">
        <div>
          <p className="font-display text-2xl font-bold text-bobb-navy">
            ₹{rec.price_rupees.toFixed(0)}
          </p>
          <p className="text-xs text-bobb-navy/50 mt-0.5">
            {rec.print_area_width_in}×{rec.print_area_height_in}in print area
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-bobb-navy/50">{rec.production_time_minutes} min</p>
          <p className="text-xs text-bobb-navy/50">production</p>
        </div>
      </div>

      {/* Selected indicator */}
      {selected && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-3 right-3 w-7 h-7 rounded-full bg-bobb-gold flex items-center justify-center"
        >
          <svg className="w-4 h-4 text-bobb-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </motion.div>
      )}
    </motion.button>
  );
}
