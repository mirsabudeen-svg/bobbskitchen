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
  const incrementRefinementsCount = useSessionStore((s) => s.incrementRefinementsCount);
  const setState = useSessionStore((s) => s.setState);

  const [selectedType, setSelectedType] = useState<RefinementType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Require an explicit selection — never silently fall back to variants[0]
  const sourceVariantId = latestDesign?.selected_variant_id ?? null;
  const sourceVariant = latestDesign?.variants.find((v) => v.variant_id === sourceVariantId);
  const refinementsLeft = 3 - (latestDesign?.refinements_count ?? 0);

  // Guard: if no variant is selected, send them back to pick one
  if (!sourceVariantId) {
    return (
      <motion.div
        key="refining-guard"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="min-h-screen bg-bobb-cream flex flex-col items-center justify-center px-8 gap-8"
      >
        <div className="text-center max-w-md">
          <div className="w-14 h-14 rounded-full bg-bobb-navy/10 flex items-center justify-center mx-auto mb-6">
            <span className="text-2xl">👆</span>
          </div>
          <h2 className="font-display text-bobb-navy text-3xl font-bold mb-3">
            Select a design first
          </h2>
          <p className="font-body text-bobb-navy/60 text-base">
            Tap one of your designs on the previous screen, then tap Refine to adjust it.
          </p>
        </div>
        <Button size="lg" onClick={() => setState(SessionState.PREVIEW)}>
          ← Back to My Designs
        </Button>
      </motion.div>
    );
  }

  async function handleRefine() {
    if (!latestDesign || !sourceVariantId || !selectedType) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.refineVariant(
        latestDesign.design_id,
        sourceVariantId,
        selectedType,
      );
      addVariant({
        variant_id: resp.new_variant_id,
        variant_number: resp.variant_number,
        style: (resp.style ?? 'illustration') as VariantStyle,
        image_url: resp.image_url,
        is_refined: true,
      });
      incrementRefinementsCount();
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
      className="min-h-screen bg-bobb-cream flex flex-col px-6 py-8 pb-28 gap-5"
    >
      {/* Header with source variant thumbnail */}
      <div className="flex items-start gap-4">
        {sourceVariant?.image_url && (
          <div className="w-16 h-16 rounded-xl overflow-hidden border-2 border-bobb-gold flex-shrink-0">
            <img
              src={sourceVariant.image_url}
              alt="Design being refined"
              className="w-full h-full object-cover"
            />
          </div>
        )}
        <div className="flex-1">
          <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-0.5">
            Refining your {sourceVariant?.style ?? 'design'}
          </p>
          <h2 className="font-display text-bobb-navy text-3xl font-bold">
            How should we adjust it?
          </h2>
          <p className="font-body text-bobb-navy/50 text-sm mt-0.5">
            {refinementsLeft} refinement{refinementsLeft !== 1 ? 's' : ''} remaining
          </p>
        </div>
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
              'rounded-card border-2 p-5 text-left transition-all duration-200 min-h-[120px]',
              selectedType === opt.type
                ? 'border-bobb-gold bg-bobb-gold/10'
                : 'border-bobb-navy/10 bg-white hover:border-bobb-navy/30',
            ].join(' ')}
          >
            <span className="text-2xl block mb-2">{opt.icon}</span>
            <p className="font-body text-bobb-navy font-semibold text-base">{opt.label}</p>
            <p className="font-body text-bobb-navy/50 text-sm mt-1">{opt.description}</p>
          </motion.button>
        ))}
      </div>

      {/* Sticky action bar */}
      <div className="fixed bottom-0 inset-x-0 bg-bobb-cream/95 backdrop-blur-sm border-t border-bobb-navy/10 px-6 py-4 flex gap-4 z-10">
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
