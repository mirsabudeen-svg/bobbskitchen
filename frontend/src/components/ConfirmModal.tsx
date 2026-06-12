import { motion, AnimatePresence } from 'framer-motion';
import { Button } from './Button';

interface ConfirmModalProps {
  open: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export function ConfirmModal({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel = 'Keep My Designs',
  onConfirm,
  onCancel,
  danger = true,
}: ConfirmModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-bobb-navy/60 z-40"
            onClick={onCancel}
          />

          {/* Sheet */}
          <motion.div
            key="sheet"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed bottom-0 inset-x-0 z-50 bg-bobb-cream rounded-t-2xl px-8 py-10 flex flex-col gap-6"
          >
            <div className="text-center">
              <h3 className="font-display text-bobb-navy text-2xl font-bold mb-2">{title}</h3>
              <p className="font-body text-bobb-navy/60 text-base">{body}</p>
            </div>
            <div className="flex flex-col gap-3">
              <Button
                variant={danger ? 'danger' : 'primary'}
                size="lg"
                fullWidth
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
              <Button variant="ghost" size="lg" fullWidth onClick={onCancel}>
                {cancelLabel}
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
