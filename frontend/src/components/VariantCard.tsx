import { motion } from 'framer-motion';
import { DesignVariant, VariantStyle } from '../types';

const STYLE_LABELS: Record<VariantStyle, string> = {
  illustration: 'Folk Art',
  geometric: 'Geometric',
  watercolor: 'Watercolour',
  minimalist: 'Minimalist',
};

const STYLE_COLORS: Record<VariantStyle, string> = {
  illustration: 'bg-bobb-saffron/20 text-bobb-saffron',
  geometric: 'bg-bobb-navy/10 text-bobb-navy',
  watercolor: 'bg-bobb-green/20 text-bobb-green',
  minimalist: 'bg-bobb-gold/20 text-bobb-navy',
};

interface VariantCardProps {
  variant: DesignVariant;
  selected: boolean;
  onSelect: (id: string) => void;
  /** Force-disable selection (defaults to disabled when generation failed). */
  disabled?: boolean;
}

export function VariantCard({ variant, selected, onSelect, disabled }: VariantCardProps) {
  const label = STYLE_LABELS[variant.style] ?? variant.style;
  const colorClass = STYLE_COLORS[variant.style] ?? 'bg-gray-100 text-gray-700';

  // Sprint 6.2 Fix 3: a variant with no image is a failed/fallback variant —
  // render a distinct failed state and make it non-selectable.
  const failed = variant.image_url === null || variant.success === false;
  const isDisabled = disabled || failed;

  return (
    <motion.button
      onClick={() => {
        if (!isDisabled) onSelect(variant.variant_id);
      }}
      disabled={isDisabled}
      whileTap={isDisabled ? undefined : { scale: 0.97 }}
      className={[
        'relative rounded-card overflow-hidden border-4 transition-all duration-200 w-full aspect-square',
        isDisabled
          ? 'border-transparent cursor-not-allowed'
          : selected
            ? 'border-bobb-gold shadow-lg shadow-bobb-gold/30'
            : 'border-transparent hover:border-bobb-navy/30',
      ].join(' ')}
    >
      {variant.image_url ? (
        <img
          src={variant.image_url}
          alt={label}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full bg-gray-200 flex flex-col items-center justify-center gap-2">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3.75m0 3.75h.008M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-body text-gray-500 text-sm">Generation failed</span>
        </div>
      )}

      {/* Style badge */}
      <div className="absolute bottom-0 inset-x-0 p-2">
        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${colorClass}`}>
          {label}
        </span>
      </div>

      {/* Selected checkmark */}
      {selected && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute top-2 right-2 w-8 h-8 rounded-full bg-bobb-gold flex items-center justify-center"
        >
          <svg className="w-5 h-5 text-bobb-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </motion.div>
      )}

      {variant.is_refined && (
        <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-bobb-green text-white text-xs font-semibold">
          Refined
        </div>
      )}
    </motion.button>
  );
}
