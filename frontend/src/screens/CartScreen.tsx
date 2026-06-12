import { motion } from 'framer-motion';
import { useState } from 'react';
import { Button } from '../components/Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

const SIZES = ['S', 'M', 'L', 'XL', 'XXL'] as const;
type Size = typeof SIZES[number];

export function CartScreen() {
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const latestDesign = useSessionStore((s) => s.latestDesign);
  const quantity = useSessionStore((s) => s.quantity);
  const nameTagText = useSessionStore((s) => s.nameTagText);
  const setQuantity = useSessionStore((s) => s.setQuantity);
  const setNameTagText = useSessionStore((s) => s.setNameTagText);
  const selectProduct = useSessionStore((s) => s.selectProduct);
  const setState = useSessionStore((s) => s.setState);

  const suggestedSize = (selectedProduct?.mockup_hint?.suggested_size ?? null) as Size | null;
  const [selectedSize, setSelectedSize] = useState<Size | null>(suggestedSize);
  const [sizeError, setSizeError] = useState(false);

  if (!selectedProduct) {
    setState(SessionState.PRODUCT_SELECTION);
    return null;
  }

  const product = selectedProduct;

  const selectedVariant =
    latestDesign?.variants.find(
      (v) => v.variant_id === latestDesign.selected_variant_id,
    ) ?? latestDesign?.variants[0];

  const unitPrice = product.price_rupees;
  const lineTotal = unitPrice * quantity;

  function handleCheckout() {
    if (!selectedSize) {
      setSizeError(true);
      return;
    }
    selectProduct({
      ...product,
      mockup_hint: { ...product.mockup_hint, suggested_size: selectedSize },
    });
    setState(SessionState.CHECKOUT);
  }

  return (
    <motion.div
      key="cart"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="min-h-screen bg-bobb-cream flex flex-col px-6 pt-8 pb-28"
    >
      <div className="mb-6">
        <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-1">
          Your Order
        </p>
        <h2 className="font-display text-bobb-navy text-3xl font-bold">
          Review & customise
        </h2>
      </div>

      {/* Design thumbnail + product name */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="flex gap-4 bg-white rounded-card border border-bobb-navy/10 p-4 mb-4"
      >
        {selectedVariant?.image_url && (
          <div className="w-20 h-20 rounded-xl overflow-hidden flex-shrink-0 border border-bobb-navy/10">
            <img
              src={selectedVariant.image_url}
              alt="Selected design"
              className="w-full h-full object-cover"
            />
          </div>
        )}
        <div className="flex flex-col justify-center">
          <p className="font-display text-bobb-navy font-semibold text-lg leading-tight">
            {selectedProduct.product_name}
          </p>
          <p className="font-body text-bobb-navy/50 text-sm capitalize mt-0.5">
            {selectedVariant?.style ?? '—'} style
          </p>
          <p className="font-body text-bobb-navy/50 text-sm mt-0.5">
            {selectedProduct.production_time_minutes} min production
          </p>
        </div>
      </motion.div>

      {/* Size selector */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12 }}
        className="bg-white rounded-card border border-bobb-navy/10 p-5 mb-4"
      >
        <div className="flex items-center justify-between mb-3">
          <p className="font-body text-bobb-navy font-semibold">
            Size <span className="text-red-500">*</span>
          </p>
          {sizeError && (
            <p className="font-body text-red-500 text-xs">Please select a size</p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          {SIZES.map((s) => (
            <button
              key={s}
              onClick={() => {
                setSelectedSize(s);
                setSizeError(false);
              }}
              className={[
                'w-12 h-12 rounded-button font-body font-semibold text-sm border-2 transition-colors',
                selectedSize === s
                  ? 'bg-bobb-navy border-bobb-navy text-white'
                  : sizeError
                  ? 'border-red-300 text-bobb-navy/60 hover:border-bobb-navy/40'
                  : 'border-bobb-navy/20 text-bobb-navy/60 hover:border-bobb-gold',
              ].join(' ')}
              aria-pressed={selectedSize === s}
            >
              {s}
            </button>
          ))}
        </div>
        {suggestedSize && (
          <p className="font-body text-bobb-navy/40 text-xs mt-2">
            Suggested: {suggestedSize}
          </p>
        )}
      </motion.div>

      {/* Quantity picker */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="bg-white rounded-card border border-bobb-navy/10 p-5 mb-4"
      >
        <div className="flex items-center justify-between">
          <p className="font-body text-bobb-navy font-semibold">Quantity</p>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setQuantity(quantity - 1)}
              disabled={quantity <= 1}
              className="w-10 h-10 rounded-full border-2 border-bobb-navy/20 flex items-center justify-center font-display text-bobb-navy text-xl disabled:opacity-30 hover:border-bobb-gold transition-colors"
            >
              −
            </button>
            <span className="font-display text-bobb-navy text-2xl font-bold w-8 text-center">
              {quantity}
            </span>
            <button
              onClick={() => setQuantity(quantity + 1)}
              disabled={quantity >= 5}
              className="w-10 h-10 rounded-full border-2 border-bobb-navy/20 flex items-center justify-center font-display text-bobb-navy text-xl disabled:opacity-30 hover:border-bobb-gold transition-colors"
            >
              +
            </button>
          </div>
        </div>
      </motion.div>

      {/* Name tag input */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-card border border-bobb-navy/10 p-5 mb-4"
      >
        <div className="flex items-start justify-between mb-2">
          <div>
            <p className="font-body text-bobb-navy font-semibold">Name tag</p>
            <p className="font-body text-bobb-navy/40 text-xs mt-0.5">
              Optional — printed inside the garment
            </p>
          </div>
          <span className="font-body text-bobb-navy/30 text-xs">
            {nameTagText.length}/15
          </span>
        </div>
        <input
          type="text"
          value={nameTagText}
          onChange={(e) => setNameTagText(e.target.value)}
          maxLength={15}
          placeholder="e.g. Arjun"
          className="w-full border-2 border-bobb-navy/20 rounded-button px-4 py-3 font-body text-bobb-navy text-base outline-none focus:border-bobb-gold transition-colors placeholder-bobb-navy/30"
        />
      </motion.div>

      {/* Order total */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="bg-white rounded-card border border-bobb-navy/10 p-5 mb-4"
      >
        <div className="flex justify-between mb-2">
          <p className="font-body text-bobb-navy/60 text-sm">
            ₹{unitPrice.toFixed(0)} × {quantity}
          </p>
          <p className="font-body text-bobb-navy/60 text-sm">
            ₹{lineTotal.toFixed(0)}
          </p>
        </div>
        <div className="border-t border-bobb-navy/10 pt-3 flex justify-between items-baseline">
          <p className="font-body text-bobb-navy font-semibold">Total</p>
          <p className="font-display text-bobb-navy text-3xl font-bold">
            ₹{lineTotal.toFixed(0)}
          </p>
        </div>
      </motion.div>

      {/* Sticky action bar */}
      <div className="fixed bottom-0 inset-x-0 bg-bobb-cream/95 backdrop-blur-sm border-t border-bobb-navy/10 px-6 py-4 flex gap-4 z-10">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => setState(SessionState.PRODUCT_SELECTION)}
        >
          ← Change
        </Button>
        <Button size="lg" fullWidth onClick={handleCheckout}>
          Checkout — ₹{lineTotal.toFixed(0)} →
        </Button>
      </div>
    </motion.div>
  );
}
