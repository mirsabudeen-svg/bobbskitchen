import { motion } from 'framer-motion';
import { LoadingPulse } from '../components/LoadingPulse';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function ProductionScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const setState = useSessionStore((s) => s.setState);

  return (
    <motion.div
      key="production"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-10"
    >
      <LoadingPulse
        label="Printing your design"
        sublabel={
          selectedProduct
            ? `${selectedProduct.product_name} · ${selectedProduct.production_time_minutes} min`
            : 'Preparing your order…'
        }
      />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="text-center"
      >
        <button
          onClick={() => setState(SessionState.SUCCESS)}
          className="font-body text-bobb-cream/30 text-xs hover:text-bobb-cream/60 transition-colors"
        >
          Skip to completion (demo)
        </button>
      </motion.div>
    </motion.div>
  );
}
