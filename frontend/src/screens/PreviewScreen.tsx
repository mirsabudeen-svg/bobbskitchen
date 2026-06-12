import { motion } from 'framer-motion';
import { useState } from 'react';
import { Button } from '../components/Button';
import { VariantCard } from '../components/VariantCard';
import { api } from '../services/api';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function PreviewScreen() {
  const latestDesign = useSessionStore((s) => s.latestDesign);
  const setState = useSessionStore((s) => s.setState);
  const setSelectedVariantId = useSessionStore((s) => s.setSelectedVariantId);
  const setRecommendations = useSessionStore((s) => s.setRecommendations);

  const [activeId, setActiveId] = useState<string | null>(
    latestDesign?.selected_variant_id ?? null,
  );
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!latestDesign) return null;

  async function handleProceed() {
    if (!activeId || !latestDesign) return;
    setLoadingRecs(true);
    setError(null);
    try {
      await api.selectVariant(latestDesign.design_id, activeId);
      setSelectedVariantId(activeId);
      const recResp = await api.generateRecommendations(latestDesign.design_id);
      setRecommendations(recResp.recommendations);
      setState(SessionState.PRODUCT_SELECTION);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load recommendations.');
    } finally {
      setLoadingRecs(false);
    }
  }

  const refinementsLeft = 3 - (latestDesign.refinements_count ?? 0);

  return (
    <motion.div
      key="preview"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-bobb-cream flex flex-col px-6 py-8 gap-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest">
            Your Designs
          </p>
          <h2 className="font-display text-bobb-navy text-3xl font-bold mt-0.5">
            Choose your favourite
          </h2>
        </div>
        {refinementsLeft > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setState(SessionState.REFINING)}
            disabled={!activeId || loadingRecs}
          >
            Refine ({refinementsLeft} left)
          </Button>
        )}
      </div>

      {error && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-red-600 text-sm"
        >
          {error}
        </motion.p>
      )}

      {/* 2×2 variant grid */}
      <div className="grid grid-cols-2 gap-4 flex-1">
        {latestDesign.variants.map((v) => (
          <VariantCard
            key={v.variant_id}
            variant={v}
            selected={v.variant_id === activeId}
            onSelect={setActiveId}
          />
        ))}
      </div>

      {/* Action bar */}
      <div className="flex gap-4">
        <Button
          variant="secondary"
          size="lg"
          onClick={() => setState(SessionState.LISTENING)}
          disabled={loadingRecs}
        >
          Start Over
        </Button>
        <Button
          size="lg"
          fullWidth
          loading={loadingRecs}
          disabled={!activeId}
          onClick={() => void handleProceed()}
        >
          {activeId ? 'Find My Product →' : 'Select a Design'}
        </Button>
      </div>
    </motion.div>
  );
}
