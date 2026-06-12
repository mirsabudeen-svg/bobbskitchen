import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function SuccessScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const reset = useSessionStore((s) => s.reset);
  const setState = useSessionStore((s) => s.setState);

  function handleReset() {
    reset();
    setState(SessionState.IDLE);
  }

  return (
    <motion.div
      key="success"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen bg-bobb-green flex flex-col items-center justify-center gap-10 px-8"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
        className="w-28 h-28 rounded-full bg-bobb-gold flex items-center justify-center"
      >
        <svg className="w-16 h-16 text-bobb-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="text-center"
      >
        <h2 className="font-display text-white text-5xl font-bold mb-3">
          Order Complete!
        </h2>
        {selectedProduct && (
          <p className="font-body text-white/70 text-xl">
            Your {selectedProduct.product_name} is being printed
          </p>
        )}
        <p className="font-body text-white/50 text-base mt-2">
          Thank you for your BOBB story
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        <Button
          variant="ghost"
          size="xl"
          onClick={handleReset}
          className="border-white/30 text-white hover:bg-white/10"
        >
          Start New Story
        </Button>
      </motion.div>
    </motion.div>
  );
}
