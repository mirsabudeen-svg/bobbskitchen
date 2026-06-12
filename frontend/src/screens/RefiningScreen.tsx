import { motion } from 'framer-motion';
import { useState } from 'react';
import { Button } from '../components/Button';
import { api } from '../services/api';
import { useSessionStore } from '../store/session';
import { RefinementType, SessionState, VariantStyle } from '../types';

interface RefinementOption {
  type: RefinementType;
  label: string;
  description: string;
  icon: string;
}

const OPTIONS: RefinementOption[] = [
  { type: 'more_minimal', label: 'More Minimal', description: 'Cleaner, simpler composition', icon: '◽' },
  { type: 'more_cultural', label: 'More Cultural', description: 'Deeper Kerala heritage elements', icon: '🪷' },
  { type: 'more_modern', label: 'More Modern', description: 'Contemporary aesthetic', icon: '◈' },
  { type: 'more_premium', label: 'More Premium', description: 'Elevated, luxury feel', icon: '✦' },
  { type: 'different_colors', label: 'New Colours', description: 'Different colour palette', icon: '🎨' },
  { type: 'different_layout', label: 'New Layout', description: 'Rearranged composition', icon: '⊞' },
];

export function RefiningScreen() {
  const latestDesign = useSessionStore((s) => s.latestDesign);
  const addVariant = useSessionStore((s) => s.addVariant);
  const setState = useSessionStore((s) => s.setState);

  const [selectedType, setSelectedType] = useState<RefinementType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedVariantId = latestDesign?.selected_variant_id
    ?? latestDesign?.variants[0]?.variant_id;

  async function handleRefine() {
    if (!latestDesign || !selectedVariantId || !selectedType) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.refineVariant(
        latestDesign.design_id,
        selectedVariantId,
        selectedType,
      );
      addVariant({
        variant_id: resp.new_variant_id,
        variant_number: resp.variant_number,
        style: (resp.style ?? 'illustration') as VariantStyle,
        image_url: resp.image_url,
        is_refined: true,
      });
      setState(SessionState.PREVIEW);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Refinement failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      key="refining"
      initial={{ opacity: 0, x: 30 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -30 }}
      transition={{ duration: 0.35 }}
      className="min-h-screen bg-bobb-cream flex flex-col px-6 py-8 gap-6"
    >
      <div>
        <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-1">
          Refinement
        </p>
        <h2 className="font-display text-bobb-navy text-3xl font-bold">
          How should we adjust it?
        </h2>
        <p className="font-body text-bobb-navy/50 text-base mt-1">
          {3 - (latestDesign?.refinements_count ?? 0)} refinement
          {3 - (latestDesign?.refinements_count ?? 0) !== 1 ? 's' : ''} remaining
        </p>
      </div>

      {error && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-red-600 text-sm">
          {error}
        </motion.p>
      )}

      <div className="grid grid-cols-2 gap-3 flex-1">
        {OPTIONS.map((opt) => (
          <motion.button
            key={opt.type}
            whileTap={{ scale: 0.97 }}
            onClick={() => setSelectedType(opt.type)}
            className={[
              'rounded-card border-2 p-4 text-left transition-all duration-200',
              selectedType === opt.type
                ? 'border-bobb-gold bg-bobb-gold/10'
                : 'border-bobb-navy/10 bg-white hover:border-bobb-navy/30',
            ].join(' ')}
          >
            <span className="text-2xl block mb-2">{opt.icon}</span>
            <p className="font-body text-bobb-navy font-semibold text-sm">{opt.label}</p>
            <p className="font-body text-bobb-navy/50 text-xs mt-0.5">{opt.description}</p>
          </motion.button>
        ))}
      </div>

      <div className="flex gap-4">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => setState(SessionState.PREVIEW)}
          disabled={loading}
        >
          ← Back
        </Button>
        <Button
          size="lg"
          fullWidth
          loading={loading}
          disabled={!selectedType}
          onClick={() => void handleRefine()}
        >
          {loading ? 'Refining…' : 'Apply Refinement →'}
        </Button>
      </div>
    </motion.div>
  );
}
