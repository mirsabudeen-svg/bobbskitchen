import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function CheckoutScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const setState = useSessionStore((s) => s.setState);

  return (
    <motion.div
      key="checkout"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="min-h-screen bg-bobb-cream flex flex-col items-center justify-center px-8 gap-10"
    >
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-full bg-bobb-navy/10 flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl">🛒</span>
        </div>
        <h2 className="font-display text-bobb-navy text-4xl font-bold mb-4">
          Checkout
        </h2>
        <p className="font-body text-bobb-navy/60 text-lg mb-2">
          Payment processing is handled at the counter.
        </p>
        {selectedProduct && (
          <p className="font-display text-bobb-navy text-3xl font-bold">
            ₹{selectedProduct.price_rupees.toFixed(0)}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-4 w-full max-w-sm">
        <Button size="xl" fullWidth onClick={() => setState(SessionState.PRODUCTION)}>
          Confirm Order →
        </Button>
        <Button
          variant="ghost"
          size="lg"
          fullWidth
          onClick={() => setState(SessionState.CART)}
        >
          ← Go Back
        </Button>
      </div>
    </motion.div>
  );
}
