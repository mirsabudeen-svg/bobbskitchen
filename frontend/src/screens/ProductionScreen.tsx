import { motion } from 'framer-motion';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function ProductionScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const shortRef = useSessionStore((s) => s.shortRef);
  const setState = useSessionStore((s) => s.setState);

  return (
    <motion.div
      key="production"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-10 px-8"
    >
      {/* Confirmation icon */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
        className="w-24 h-24 rounded-full bg-bobb-green/20 flex items-center justify-center"
      >
        <svg className="w-12 h-12 text-bobb-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-center"
      >
        <h1 className="font-display text-white text-4xl font-bold mb-3">
          Order received
        </h1>
        <p className="font-body text-bobb-cream/70 text-lg">
          Please pay at the counter
        </p>
        {selectedProduct && (
          <p className="font-body text-bobb-cream/50 text-base mt-1">
            We'll call your name when your {selectedProduct.product_name} is ready
          </p>
        )}
      </motion.div>

      {/* Order reference */}
      {shortRef && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-white/10 rounded-2xl px-10 py-5 text-center"
        >
          <p className="font-body text-bobb-cream/50 text-xs uppercase tracking-widest mb-1">
            Your order reference
          </p>
          <p className="font-display text-bobb-gold text-5xl font-bold tracking-widest">
            {shortRef}
          </p>
          <p className="font-body text-bobb-cream/40 text-xs mt-2">
            Show this to a BOBB team member
          </p>
        </motion.div>
      )}

      {/* DEV-only skip — removed from production build */}
      {import.meta.env.DEV && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2 }}>
          <button
            onClick={() => setState(SessionState.SUCCESS)}
            className="font-body text-bobb-cream/20 text-xs hover:text-bobb-cream/40 transition-colors"
          >
            [DEV] Skip to completion
          </button>
        </motion.div>
      )}
    </motion.div>
  );
}
