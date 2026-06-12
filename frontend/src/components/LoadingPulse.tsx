import { motion } from 'framer-motion';

interface LoadingPulseProps {
  label?: string;
  sublabel?: string;
}

const DOT_VARIANTS = {
  start: { y: 0 },
  end: { y: -12 },
};

export function LoadingPulse({ label, sublabel }: LoadingPulseProps) {
  return (
    <div className="flex flex-col items-center gap-8">
      <div className="flex gap-3">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="w-4 h-4 rounded-full bg-bobb-gold"
            variants={DOT_VARIANTS}
            initial="start"
            animate="end"
            transition={{
              repeat: Infinity,
              repeatType: 'mirror',
              duration: 0.5,
              delay: i * 0.12,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      {label && (
        <div className="text-center">
          <p className="text-bobb-navy font-display text-2xl font-semibold">{label}</p>
          {sublabel && (
            <p className="text-bobb-navy/60 font-body text-base mt-2">{sublabel}</p>
          )}
        </div>
      )}
    </div>
  );
}
