import { motion } from 'framer-motion';
import { useState } from 'react';
import { Button } from '../components/Button';
import { api } from '../services/api';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function CheckoutScreen() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const selectedProduct = useSessionStore((s) => s.selectedProduct);
  const latestDesign = useSessionStore((s) => s.latestDesign);
  const quantity = useSessionStore((s) => s.quantity);
  const nameTagText = useSessionStore((s) => s.nameTagText);
  const customerName = useSessionStore((s) => s.customerName);
  const customerPhone = useSessionStore((s) => s.customerPhone);
  const setCustomerName = useSessionStore((s) => s.setCustomerName);
  const setCustomerPhone = useSessionStore((s) => s.setCustomerPhone);
  const setOrderId = useSessionStore((s) => s.setOrderId);
  const setState = useSessionStore((s) => s.setState);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nameError, setNameError] = useState(false);

  if (!selectedProduct) {
    setState(SessionState.CART);
    return null;
  }

  const selectedVariant =
    latestDesign?.variants.find(
      (v) => v.variant_id === latestDesign.selected_variant_id,
    ) ?? latestDesign?.variants[0];

  const lineTotal = selectedProduct.price_rupees * quantity;

  async function handleConfirm() {
    if (!customerName.trim()) {
      setNameError(true);
      return;
    }
    if (!sessionId || !selectedVariant || !latestDesign || !selectedProduct) {
      setError('Session data missing. Please go back and try again.');
      return;
    }
    const product = selectedProduct;

    setLoading(true);
    setError(null);
    try {
      const order = await api.createOrder({
        session_id: sessionId,
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim() || undefined,
        name_tag_text: nameTagText.trim() || undefined,
        items: [
          {
            design_variant_id: selectedVariant.variant_id,
            product_id: product.product_id,
            product_name: product.product_name,
            size: product.mockup_hint?.suggested_size ?? null,
            color: product.mockup_hint?.suggested_color ?? 'natural',
            quantity,
            unit_price_paise: product.price_paise,
          },
        ],
      });
      setOrderId(order.order_id);
      setState(SessionState.PRODUCTION);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not place order. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      key="checkout"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="min-h-screen bg-bobb-cream flex flex-col px-6 pt-8 pb-28"
    >
      <div className="mb-6">
        <p className="font-body text-bobb-saffron text-xs uppercase tracking-widest mb-1">
          Almost there
        </p>
        <h2 className="font-display text-bobb-navy text-3xl font-bold">
          Your details
        </h2>
        <p className="font-body text-bobb-navy/50 text-base mt-1">
          So we can prepare your garment and let you know when it's ready.
        </p>
      </div>

      {/* Customer name */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-4"
      >
        <label className="block font-body text-bobb-navy font-semibold text-sm mb-2">
          Your name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={customerName}
          onChange={(e) => {
            setCustomerName(e.target.value);
            setNameError(false);
          }}
          placeholder="First name or full name"
          className={[
            'w-full border-2 rounded-button px-5 py-4 font-body text-bobb-navy text-lg',
            'outline-none transition-colors placeholder-bobb-navy/30',
            nameError ? 'border-red-400 bg-red-50' : 'border-bobb-navy/20 focus:border-bobb-gold',
          ].join(' ')}
        />
        {nameError && (
          <p className="text-red-500 text-sm mt-1">Name is required to place the order</p>
        )}
      </motion.div>

      {/* Phone */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-6"
      >
        <label className="block font-body text-bobb-navy font-semibold text-sm mb-2">
          WhatsApp number{' '}
          <span className="text-bobb-navy/40 font-normal">(optional)</span>
        </label>
        <input
          type="tel"
          value={customerPhone}
          onChange={(e) => setCustomerPhone(e.target.value)}
          placeholder="+91 98765 43210"
          className="w-full border-2 border-bobb-navy/20 rounded-button px-5 py-4 font-body text-bobb-navy text-lg outline-none focus:border-bobb-gold transition-colors placeholder-bobb-navy/30"
        />
        <p className="font-body text-bobb-navy/40 text-xs mt-1">
          We'll send your design preview before printing
        </p>
      </motion.div>

      {/* Order summary */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-card border border-bobb-navy/10 p-5 mb-4"
      >
        <p className="font-body text-bobb-navy/50 text-xs uppercase tracking-widest mb-3">
          Order summary
        </p>
        <div className="flex gap-4 items-start mb-3">
          {selectedVariant?.image_url && (
            <div className="w-14 h-14 rounded-lg overflow-hidden flex-shrink-0 border border-bobb-navy/10">
              <img src={selectedVariant.image_url} alt="Design" className="w-full h-full object-cover" />
            </div>
          )}
          <div className="flex-1">
            <p className="font-body text-bobb-navy font-semibold text-sm">
              {selectedProduct.product_name}
            </p>
            <p className="font-body text-bobb-navy/50 text-xs capitalize mt-0.5">
              {selectedVariant?.style ?? '—'} · Qty {quantity}
              {nameTagText ? ` · Tag: "${nameTagText}"` : ''}
            </p>
          </div>
        </div>
        <div className="border-t border-bobb-navy/10 pt-3 flex justify-between items-baseline">
          <p className="font-body text-bobb-navy font-semibold text-sm">Total</p>
          <p className="font-display text-bobb-navy text-2xl font-bold">
            ₹{lineTotal.toFixed(0)}
          </p>
        </div>
        <p className="font-body text-bobb-navy/40 text-xs mt-2">
          Payment collected at the counter
        </p>
      </motion.div>

      {error && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-red-600 text-sm mb-4"
        >
          {error}
        </motion.p>
      )}

      {/* Sticky action bar */}
      <div className="fixed bottom-0 inset-x-0 bg-bobb-cream/95 backdrop-blur-sm border-t border-bobb-navy/10 px-6 py-4 flex gap-4 z-10">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => setState(SessionState.CART)}
          disabled={loading}
        >
          ← Back
        </Button>
        <Button
          size="lg"
          fullWidth
          loading={loading}
          onClick={() => void handleConfirm()}
        >
          {loading ? 'Placing order…' : 'Confirm Order →'}
        </Button>
      </div>
    </motion.div>
  );
}
