import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { ProductCard } from '../components/ProductCard';
import { useSessionStore } from '../store/session';
import { ProductRecommendation, SessionState } from '../types';

export function ProductSelectionScreen() {
  const recommendations = useSessionStore((s) => s.recommendations);
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const selectProduct = useSessionStore((s) => s.selectProduct);
  const setState = useSessionStore((s) => s.setState);

  if (!recommendations) return null;

  function handleSelect(rec: ProductRecommendation) {
    selectProduct(rec);
  }

  return (
    <motion.div
      key="product_selection"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-bobb-cream flex flex-col px-6 py-8 gap-6"
    >
      <div>
        <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-1">
          Recommendations
        </p>
        <h2 className="font-display text-bobb-navy text-3xl font-bold">
          Choose your product
        </h2>
        <p className="font-body text-bobb-navy/50 text-base mt-1">
          Matched to your design's style and complexity
        </p>
      </div>

      <div className="flex flex-col gap-4 flex-1">
        {recommendations.map((rec, i) => (
          <motion.div
            key={rec.product_id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <ProductCard
              rec={rec}
              selected={selectedProduct?.product_id === rec.product_id}
              onSelect={handleSelect}
            />
          </motion.div>
        ))}
      </div>

      <div className="flex gap-4">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => setState(SessionState.PREVIEW)}
        >
          ← Back
        </Button>
        <Button
          size="lg"
          fullWidth
          disabled={!selectedProduct}
          onClick={() => setState(SessionState.CART)}
        >
          {selectedProduct ? `Add to Cart — ₹${selectedProduct.price_rupees.toFixed(0)}` : 'Select a Product'}
        </Button>
      </div>
    </motion.div>
  );
}
