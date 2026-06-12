import { motion } from 'framer-motion';
import { useSessionStore } from '../store/session';

const STYLE_NAMES = ['Folk Art', 'Geometric', 'Watercolour', 'Minimalist'];

export function GeneratingScreen() {
  const progress = useSessionStore((s) => s.generatingProgress);
  const total = useSessionStore((s) => s.totalVariants);
  const variants = useSessionStore((s) => s.latestDesign?.variants ?? []);

  const totalCount = total || 4;

  return (
    <motion.div
      key="generating"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-10 px-8"
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

      {/* 2×2 grid — reveals actual images as variant_ready WS events arrive */}
      <div className="grid grid-cols-2 gap-4 w-full max-w-sm">
        {Array.from({ length: totalCount }).map((_, i) => {
          const variant = variants[i];
          const hasImage = !!variant?.image_url;
          // Sprint 6.2 Fix 3: a received variant with no image failed — show a
          // failed tile instead of an endless spinner.
          const isFailed = !!variant && !hasImage && variant.success === false;
          const isGenerating = !hasImage && !isFailed;

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0.25 }}
              animate={{ opacity: hasImage ? 1 : 0.4 }}
              transition={{ duration: 0.5 }}
              className={[
                'relative aspect-square rounded-card overflow-hidden border-2',
                hasImage
                  ? 'border-bobb-gold'
                  : 'border-bobb-cream/10 bg-bobb-cream/5 flex flex-col items-center justify-center gap-2',
              ].join(' ')}
            >
              {hasImage ? (
                <>
                  <motion.img
                    key={variant.image_url!}
                    src={variant.image_url!}
                    alt={STYLE_NAMES[i] ?? `Style ${i + 1}`}
                    initial={{ opacity: 0, scale: 1.04 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.45 }}
                    className="w-full h-full object-cover"
                  />
                  {/* Gold checkmark overlay */}
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="absolute top-2 right-2 w-7 h-7 rounded-full bg-bobb-gold flex items-center justify-center"
                  >
                    <svg className="w-4 h-4 text-bobb-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </motion.div>
                  {/* Style label */}
                  <div className="absolute bottom-0 inset-x-0 bg-bobb-navy/60 px-2 py-1">
                    <span className="font-body text-bobb-cream text-xs">
                      {STYLE_NAMES[i] ?? `Style ${i + 1}`}
                    </span>
                  </div>
                </>
              ) : (
                <>
                  {isGenerating && (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                      className="w-8 h-8 rounded-full border-2 border-t-bobb-gold border-bobb-cream/20"
                    />
                  )}
                  {isFailed && (
                    <span className="font-body text-red-400 text-xs font-semibold">
                      Generation failed
                    </span>
                  )}
                  <span className="font-body text-bobb-cream/50 text-xs">
                    {STYLE_NAMES[i] ?? `Style ${i + 1}`}
                  </span>
                </>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-sm">
        <div className="flex justify-between text-bobb-cream/50 text-sm mb-2">
          <span>{progress} of {totalCount} complete</span>
          <span>{Math.round((progress / totalCount) * 100)}%</span>
        </div>
        <div className="h-2 rounded-full bg-bobb-cream/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-bobb-gold"
            animate={{ width: `${(progress / totalCount) * 100}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
