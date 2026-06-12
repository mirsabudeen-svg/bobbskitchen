import { motion } from 'framer-motion';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

/** Kiosk waiting screen. Fullscreen dark navy — tap anywhere to begin. */
export function IdleScreen() {
  const setState = useSessionStore((s) => s.setState);

  return (
    <motion.div
      key="idle"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-10 cursor-pointer select-none"
      onClick={() => setState(SessionState.GREETING)}
    >
      {/* Logo mark */}
      <motion.div
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="flex flex-col items-center gap-4"
      >
        <div className="w-24 h-24 rounded-full border-4 border-bobb-gold flex items-center justify-center">
          <span className="font-display text-bobb-gold text-3xl font-bold tracking-tight">B</span>
        </div>
        <h1 className="font-display text-bobb-cream text-5xl font-bold tracking-tight">
          BOBB
        </h1>
        <p className="font-body text-bobb-gold text-sm uppercase tracking-widest">
          Kerala Stories · Wearable Art
        </p>
      </motion.div>

      {/* Pulsing call to action */}
      <motion.div
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
        className="flex flex-col items-center gap-3"
      >
        <div className="w-20 h-20 rounded-full border-2 border-bobb-gold/40 flex items-center justify-center">
          <div className="w-14 h-14 rounded-full border-2 border-bobb-gold/70 flex items-center justify-center">
            <div className="w-8 h-8 rounded-full bg-bobb-gold" />
          </div>
        </div>
        <p className="font-body text-bobb-cream/70 text-lg">Touch to begin</p>
      </motion.div>
    </motion.div>
  );
}
