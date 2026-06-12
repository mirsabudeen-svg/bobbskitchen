import { motion } from 'framer-motion';
import { LoadingPulse } from '../components/LoadingPulse';

const PHRASES = [
  'Listening to your Kerala story…',
  'Finding the themes and emotions…',
  'Consulting the design spirit…',
  'Weaving the art strategy…',
];

export function ThinkingScreen() {
  return (
    <motion.div
      key="thinking"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-12"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="w-24 h-24 rounded-full border-4 border-bobb-gold/30 flex items-center justify-center"
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 3, ease: 'linear' }}
          className="w-16 h-16 rounded-full border-4 border-t-bobb-gold border-bobb-gold/10"
        />
      </motion.div>

      <div className="text-center">
        <LoadingPulse />
        <motion.div className="mt-8 h-8 overflow-hidden">
          {PHRASES.map((phrase, i) => (
            <motion.p
              key={phrase}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: [0, 1, 1, 0], y: [20, 0, 0, -20] }}
              transition={{
                delay: i * 2,
                duration: 2,
                times: [0, 0.15, 0.85, 1],
              }}
              className="font-display text-bobb-cream text-xl absolute inset-x-0 text-center"
            >
              {phrase}
            </motion.p>
          ))}
        </motion.div>
      </div>

      <p className="font-body text-bobb-cream/40 text-sm">
        Step 2 of 3 — Understanding your story
      </p>
    </motion.div>
  );
}
