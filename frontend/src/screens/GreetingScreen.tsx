import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { useSessionStore } from '../store/session';
import { SessionState } from '../types';

export function GreetingScreen() {
  const setState = useSessionStore((s) => s.setState);

  return (
    <motion.div
      key="greeting"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-bobb-cream flex flex-col items-center justify-center gap-12 px-8"
    >
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="text-center max-w-xl"
      >
        <p className="font-body text-bobb-saffron text-sm uppercase tracking-widest mb-4">
          Welcome to BOBB
        </p>
        <h1 className="font-display text-bobb-navy text-5xl font-bold leading-tight mb-6">
          Every Kerala story deserves to be worn
        </h1>
        <p className="font-body text-bobb-navy/60 text-xl leading-relaxed">
          Share a memory, a place, or a feeling. Our AI will weave it into a
          unique design — printed on quality fabric, ready in minutes.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3 }}
      >
        <Button size="xl" onClick={() => setState(SessionState.LISTENING)} className="min-w-64">
          Tell Your Story →
        </Button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="flex gap-10 text-center"
      >
        {['10–14 min journey', 'Kerala art styles', 'DTF quality print'].map((f) => (
          <div key={f} className="flex flex-col items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-bobb-gold" />
            <p className="font-body text-bobb-navy/50 text-sm">{f}</p>
          </div>
        ))}
      </motion.div>
    </motion.div>
  );
}
