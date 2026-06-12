import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function CartScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const latestDesign = useSessionStore((s) => s.latestDesign);
  const setState = useSessionStore((s) => s.setState);

  if (!selectedProduct) {
    setState(SessionState.PRODUCT_SELECTION);
    return null;
  }

  const selectedVariant = latestDesign?.variants.find(
    (v) => v.variant_id === latestDesign.selected_variant_id,
  ) ?? latestDesign?.variants[0];

  return (
    <motion.div
      key="cart"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="min-h-screen bg-bobb-cream flex flex-col px-6 py-8 gap-6"
    >
      <div>
        <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-1">
          Your Order
        </p>
        <h2 className="font-display text-bobb-navy text-3xl font-bold">
          Review & Checkout
        </h2>
      </div>

      {/* Design preview */}
      {selectedVariant?.image_url && (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="rounded-card overflow-hidden border-2 border-bobb-navy/10"
        >
          <img
            src={selectedVariant.image_url}
            alt="Selected design"
            className="w-full aspect-square object-cover"
          />
        </motion.div>
      )}

      {/* Order summary */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-card border border-bobb-navy/10 p-5 space-y-3"
      >
        <div className="flex justify-between">
          <p className="font-body text-bobb-navy/70 text-sm">Product</p>
          <p className="font-body text-bobb-navy font-semibold text-sm">{selectedProduct.product_name}</p>
        </div>
        <div className="flex justify-between">
          <p className="font-body text-bobb-navy/70 text-sm">Style</p>
          <p className="font-body text-bobb-navy font-semibold text-sm capitalize">
            {selectedVariant?.style ?? '—'}
          </p>
        </div>
        <div className="flex justify-between">
          <p className="font-body text-bobb-navy/70 text-sm">Production time</p>
          <p className="font-body text-bobb-navy font-semibold text-sm">
            {selectedProduct.production_time_minutes} minutes
          </p>
        </div>
        <div className="border-t border-bobb-navy/10 pt-3 flex justify-between">
          <p className="font-body text-bobb-navy font-semibold">Total</p>
          <p className="font-display text-bobb-navy text-2xl font-bold">
            ₹{selectedProduct.price_rupees.toFixed(0)}
          </p>
        </div>
      </motion.div>

      <div className="flex gap-4 mt-auto">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => setState(SessionState.PRODUCT_SELECTION)}
        >
          ← Change
        </Button>
        <Button
          size="lg"
          fullWidth
          onClick={() => setState(SessionState.CHECKOUT)}
        >
          Proceed to Checkout →
        </Button>
      </div>
    </motion.div>
  );
}
