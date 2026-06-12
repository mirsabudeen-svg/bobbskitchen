import { motion } from 'framer-motion';
import { Button } from './Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function SessionResumeOverlay() {
  const pendingReconnect = useSessionStore((s) => s.pendingReconnect);
  const applyReconnect = useSessionStore((s) => s.applyReconnect);
  const setPendingReconnect = useSessionStore((s) => s.setPendingReconnect);
  const reset = useSessionStore((s) => s.reset);
  const setState = useSessionStore((s) => s.setState);

  if (!pendingReconnect) return null;

  const hasDesign = !!pendingReconnect.latest_design;
  const variantCount = pendingReconnect.latest_design?.variants.length ?? 0;
  const thumbnailUrl = pendingReconnect.latest_design?.variants[0]?.image_url ?? null;

  function handleContinue() {
    applyReconnect();
  }

  function handleStartFresh() {
    setPendingReconnect(null);
    reset();
    setState(SessionState.GREETING);
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-bobb-navy/80 z-50 flex items-center justify-center px-8"
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
        className="bg-bobb-cream rounded-2xl p-8 w-full max-w-md flex flex-col gap-6"
      >
        <div className="text-center">
          <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-3">
            Welcome back
          </p>
          <h2 className="font-display text-bobb-navy text-3xl font-bold mb-2">
            We saved your session
          </h2>
          <p className="font-body text-bobb-navy/60 text-base">
            {hasDesign
              ? `Your ${variantCount} design${variantCount !== 1 ? 's are' : ' is'} ready to continue.`
              : 'Your story is ready to continue.'}
          </p>
        </div>

        {thumbnailUrl && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15 }}
            className="rounded-xl overflow-hidden border-2 border-bobb-gold/40 aspect-square w-32 mx-auto"
          >
            <img src={thumbnailUrl} alt="Your design" className="w-full h-full object-cover" />
          </motion.div>
        )}

        <div className="flex flex-col gap-3">
          <Button size="lg" fullWidth onClick={handleContinue}>
            Continue My Session →
          </Button>
          <Button variant="ghost" size="lg" fullWidth onClick={handleStartFresh}>
            Start a New Story
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
