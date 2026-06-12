import { motion } from 'framer-motion';
import { useState } from 'react';
import { Button } from '../components/Button';
import { api } from '../services/api';
import { useSessionStore } from '../store/session';
import { SessionState, VariantStyle } from '../types';

export function ClarifyingScreen() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const extractedStory = useSessionStore((s) => s.extractedStory);
  const setState = useSessionStore((s) => s.setState);
  const setLatestDesign = useSessionStore((s) => s.setLatestDesign);
  const setPipelineError = useSessionStore((s) => s.setPipelineError);

  const [loading, setLoading] = useState(false);

  const question =
    extractedStory?.clarification_questions?.[0] ??
    'Could you tell us a bit more about your story?';

  async function handleContinue() {
    if (!sessionId || !extractedStory) {
      setState(SessionState.LISTENING);
      return;
    }
    setLoading(true);
    setPipelineError(null);
    try {
      setState(SessionState.THINKING);
      const storyForDesign = {
        ...extractedStory,
        clarification_questions: extractedStory.clarification_questions ?? [],
      };
      const designResp = await api.generateDesign(sessionId, storyForDesign);
      setState(SessionState.GENERATING);
      setLatestDesign({
        design_id: designResp.design_id,
        variants: [],
        selected_variant_id: null,
        refinements_count: 0,
        design_locked: false,
      });

      const genResp = await api.generateImages(sessionId, designResp.design_id);
      setLatestDesign({
        design_id: designResp.design_id,
        variants: genResp.variants.map((v) => ({
          variant_id: v.variant_id,
          variant_number: v.variant_number,
          style: v.style as VariantStyle,
          image_url: v.image_url,
          is_refined: false,
          success: v.success,
        })),
        selected_variant_id: null,
        refinements_count: 0,
        design_locked: false,
      });

      setState(SessionState.PREVIEW);
    } catch (e) {
      setPipelineError(e instanceof Error ? e.message : 'Something went wrong. Please try again.');
      setState(SessionState.LISTENING);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      key="clarifying"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-bobb-cream flex flex-col items-center justify-center px-8 gap-10"
    >
      <div className="text-center max-w-lg">
        <div className="w-14 h-14 rounded-full bg-bobb-gold/20 flex items-center justify-center mx-auto mb-6">
          <span className="text-2xl">💭</span>
        </div>
        <p className="font-body text-bobb-saffron text-sm uppercase tracking-widest mb-4">
          One small question
        </p>
        <h2 className="font-display text-bobb-navy text-3xl font-bold mb-4">
          {question}
        </h2>
        <p className="font-body text-bobb-navy/50 text-base">
          A little more detail helps us create something truly personal for you.
        </p>
      </div>

      <div className="flex flex-col gap-3 w-full max-w-sm">
        <Button
          size="lg"
          fullWidth
          onClick={() => setState(SessionState.LISTENING)}
          disabled={loading}
        >
          Add More Detail →
        </Button>
        <Button
          variant="ghost"
          size="lg"
          fullWidth
          loading={loading}
          onClick={() => void handleContinue()}
        >
          {loading ? 'Creating your designs…' : 'Continue Anyway'}
        </Button>
      </div>
    </motion.div>
  );
}
