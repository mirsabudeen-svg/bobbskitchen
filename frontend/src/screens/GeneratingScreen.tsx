import { motion } from 'framer-motion';
import { useSessionStore } from '../store/session';

const STYLE_NAMES = ['Folk Art', 'Geometric', 'Watercolour', 'Minimalist'];

export function GeneratingScreen() {
  const progress = useSessionStore((s) => s.generatingProgress);
  const total = useSessionStore((s) => s.totalVariants);

  return (
    <motion.div
      key="generating"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-12 px-8"
    >
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <p className="font-body text-bobb-saffron text-sm uppercase tracking-widest mb-3">
          Step 3 of 3
        </p>
        <h2 className="font-display text-bobb-cream text-4xl font-bold">
          Creating your designs
        </h2>
        <p className="font-body text-bobb-cream/50 text-lg mt-2">
          Four unique Kerala art styles, just for you
        </p>
      </motion.div>

      {/* 2×2 progress grid */}
      <div className="grid grid-cols-2 gap-4 w-full max-w-sm">
        {Array.from({ length: total || 4 }).map((_, i) => {
          const done = i < progress;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0.3 }}
              animate={{ opacity: done ? 1 : 0.3 }}
              transition={{ duration: 0.4 }}
              className={[
                'aspect-square rounded-card border-2 flex flex-col items-center justify-center gap-2',
                done
                  ? 'border-bobb-gold bg-bobb-gold/10'
                  : 'border-bobb-cream/10 bg-bobb-cream/5',
              ].join(' ')}
            >
              {done ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-8 h-8 rounded-full bg-bobb-gold flex items-center justify-center"
                >
                  <svg className="w-5 h-5 text-bobb-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </motion.div>
              ) : (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                  className="w-8 h-8 rounded-full border-2 border-t-bobb-gold border-bobb-cream/20"
                />
              )}
              <span className="font-body text-bobb-cream/60 text-xs">
                {STYLE_NAMES[i] ?? `Style ${i + 1}`}
              </span>
            </motion.div>
          );
        })}
      </div>

      <div className="w-full max-w-sm">
        <div className="flex justify-between text-bobb-cream/50 text-sm mb-2">
          <span>{progress} of {total || 4} complete</span>
          <span>{Math.round((progress / (total || 4)) * 100)}%</span>
        </div>
        <div className="h-2 rounded-full bg-bobb-cream/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-bobb-gold"
            animate={{ width: `${(progress / (total || 4)) * 100}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
