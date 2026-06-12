import { motion } from 'framer-motion';
import { Button } from './Button';

interface IdleWarningOverlayProps {
  secondsLeft: number;
  onDismiss: () => void;
}

export function IdleWarningOverlay({ secondsLeft, onDismiss }: IdleWarningOverlayProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-bobb-navy/75 z-50 flex items-center justify-center px-8"
      onClick={onDismiss}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 280, damping: 24 }}
        className="bg-bobb-cream rounded-2xl p-10 w-full max-w-sm flex flex-col items-center gap-6 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Countdown ring */}
        <div className="relative w-24 h-24 flex items-center justify-center">
          <svg className="absolute inset-0 -rotate-90" viewBox="0 0 96 96">
            <circle
              cx="48" cy="48" r="42"
              fill="none" stroke="currentColor"
              strokeWidth="6"
              className="text-bobb-navy/10"
            />
            <motion.circle
              cx="48" cy="48" r="42"
              fill="none" stroke="currentColor"
              strokeWidth="6"
              strokeLinecap="round"
              className="text-bobb-gold"
              strokeDasharray={2 * Math.PI * 42}
              animate={{
                strokeDashoffset: 2 * Math.PI * 42 * (1 - secondsLeft / 30),
              }}
              transition={{ duration: 0.9, ease: 'linear' }}
            />
          </svg>
          <span className="font-display text-bobb-navy text-3xl font-bold">{secondsLeft}</span>
        </div>

        <div>
          <h3 className="font-display text-bobb-navy text-2xl font-bold mb-2">
            Still there?
          </h3>
          <p className="font-body text-bobb-navy/60 text-base">
            We'll reset in {secondsLeft} second{secondsLeft !== 1 ? 's' : ''} to let the next
            customer get started.
          </p>
        </div>

        <Button size="lg" fullWidth onClick={onDismiss}>
          I'm Still Here →
        </Button>
      </motion.div>
    </motion.div>
  );
}
