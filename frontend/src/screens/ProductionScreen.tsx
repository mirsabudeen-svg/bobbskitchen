import { motion } from 'framer-motion';
import { LoadingPulse } from '../components/LoadingPulse';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function ProductionScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const orderId = useSessionStore((s) => s.orderId);
  const setState = useSessionStore((s) => s.setState);

  // Short human-readable ref from UUID (last 6 hex chars)
  const orderRef = orderId ? orderId.slice(-6).toUpperCase() : null;

  return (
    <motion.div
      key="production"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-10 px-8"
    >
      <LoadingPulse
        label="Printing your design"
        sublabel={
          selectedProduct
            ? `${selectedProduct.product_name} · ~${selectedProduct.production_time_minutes} min`
            : 'Preparing your order…'
        }
      />

      {/* Order reference — helps staff match garment to customer */}
      {orderRef && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-center"
        >
          <p className="font-body text-bobb-cream/40 text-xs uppercase tracking-widest mb-1">
            Order reference
          </p>
          <p className="font-display text-bobb-gold text-4xl font-bold tracking-widest">
            #{orderRef}
          </p>
          <p className="font-body text-bobb-cream/40 text-xs mt-1">
            Show this to a BOBB team member
          </p>
        </motion.div>
      )}

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="text-center"
      >
        <button
          onClick={() => setState(SessionState.SUCCESS)}
          className="font-body text-bobb-cream/25 text-xs hover:text-bobb-cream/50 transition-colors"
        >
          Skip to completion (demo)
        </button>
      </motion.div>
    </motion.div>
  );
}
