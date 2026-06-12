import { motion } from 'framer-motion';
import { useState } from 'react';
import { Button } from '../components/Button';
import { api } from '../services/api';
import { useSessionStore } from '../store/session';
import { SessionState, VariantStyle } from '../types';

const EXAMPLES = [
  'I grew up fishing on the backwaters of Alappuzha with my grandfather…',
  'Every Onam we gathered under the coconut palms at our family home in Thrissur…',
  "The smell of spices from my grandmother's kitchen in Kozhikode stays with me…",
];

export function ListeningScreen() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const storyText = useSessionStore((s) => s.storyText);
  const setStoryText = useSessionStore((s) => s.setStoryText);
  const setExtractedStory = useSessionStore((s) => s.setExtractedStory);
  const setLatestDesign = useSessionStore((s) => s.setLatestDesign);
  const setState = useSessionStore((s) => s.setState);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!sessionId || storyText.trim().length < 10) return;
    setLoading(true);
    setError(null);
    try {
      setState(SessionState.THINKING);
      const storyResp = await api.submitStory(sessionId, storyText.trim());
      setExtractedStory({
        ...storyResp.story,
        needs_clarification: storyResp.needs_clarification,
        clarification_questions: storyResp.clarification_question
          ? [storyResp.clarification_question]
          : [],
      });

      const designResp = await api.generateDesign(sessionId, storyResp.story);
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
        })),
        selected_variant_id: null,
        refinements_count: 0,
        design_locked: false,
      });

      setState(SessionState.PREVIEW);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Please try again.');
      setState(SessionState.LISTENING);
    } finally {
      setLoading(false);
    }
  }

  const charCount = storyText.trim().length;
  const isReady = charCount >= 10 && !loading;

  return (
    <motion.div
      key="listening"
      initial={{ opacity: 0, x: 30 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -30 }}
      transition={{ duration: 0.35 }}
      className="min-h-screen bg-bobb-cream flex flex-col items-center justify-center px-8 py-12 gap-8"
    >
      <div className="w-full max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6"
        >
          <p className="font-body text-bobb-saffron text-sm uppercase tracking-widest mb-2">
            Step 1 of 3
          </p>
          <h2 className="font-display text-bobb-navy text-4xl font-bold">
            Share your story
          </h2>
          <p className="font-body text-bobb-navy/60 text-lg mt-2">
            A memory, a place, a person — anything Kerala means to you.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <textarea
            className={[
              'w-full h-48 rounded-card border-2 p-5 font-body text-lg text-bobb-navy',
              'bg-white placeholder-bobb-navy/30 resize-none outline-none transition-colors',
              'focus:border-bobb-gold',
              error ? 'border-red-400' : 'border-bobb-navy/20',
            ].join(' ')}
            placeholder="I grew up…"
            value={storyText}
            onChange={(e) => setStoryText(e.target.value)}
            maxLength={600}
            disabled={loading}
          />
          <div className="flex justify-between mt-2 text-sm text-bobb-navy/40">
            <span>{charCount < 10 ? `${10 - charCount} more characters needed` : ''}</span>
            <span>{charCount}/600</span>
          </div>
        </motion.div>

        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 text-red-600 text-sm"
          >
            {error}
          </motion.p>
        )}

        {!storyText && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-4 space-y-2"
          >
            <p className="font-body text-bobb-navy/40 text-sm">Try one of these…</p>
            {EXAMPLES.map((p) => (
              <button
                key={p}
                onClick={() => setStoryText(p)}
                className="block w-full text-left px-4 py-3 rounded-button border border-bobb-navy/10 bg-bobb-navy/5 hover:bg-bobb-navy/10 transition-colors text-sm text-bobb-navy/70 font-body"
              >
                "{p}"
              </button>
            ))}
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
          className="mt-6 flex gap-4"
        >
          <Button
            variant="ghost"
            size="lg"
            onClick={() => setState(SessionState.GREETING)}
            disabled={loading}
          >
            ← Back
          </Button>
          <Button
            size="lg"
            fullWidth
            loading={loading}
            disabled={!isReady}
            onClick={() => void handleSubmit()}
          >
            {loading ? 'Creating your design…' : 'Create My Design →'}
          </Button>
        </motion.div>
      </div>
    </motion.div>
  );
}
