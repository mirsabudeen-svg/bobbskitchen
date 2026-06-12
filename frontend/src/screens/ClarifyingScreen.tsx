import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function ClarifyingScreen() {
  const extractedStory = useSessionStore((s) => s.extractedStory);
  const setState = useSessionStore((s) => s.setState);

  const question = extractedStory?.clarification_questions?.[0]
    ?? 'Could you tell us a bit more about your story?';

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
          Your additional detail will help us create a more personal design.
        </p>
      </div>

      <div className="flex flex-col gap-4 w-full max-w-sm">
        <Button size="lg" fullWidth onClick={() => setState(SessionState.LISTENING)}>
          Add More Detail →
        </Button>
        <Button
          variant="ghost"
          size="lg"
          fullWidth
          onClick={() => setState(SessionState.THINKING)}
        >
          Continue Anyway
        </Button>
      </div>
    </motion.div>
  );
}
