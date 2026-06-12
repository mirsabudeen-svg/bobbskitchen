import { motion, AnimatePresence } from 'framer-motion';
import { useSessionStore } from '../store/session';

export function ConnectionBanner() {
  const wsConnected = useSessionStore((s) => s.wsConnected);
  const sessionId = useSessionStore((s) => s.sessionId);

  // Only show after a session is established — not during initial load
  const show = !!sessionId && !wsConnected;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="banner"
          initial={{ y: -40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed top-0 inset-x-0 z-30 bg-bobb-saffron/95 py-2 px-6 flex items-center justify-center gap-3"
        >
          <span className="w-2 h-2 rounded-full bg-white animate-pulse flex-shrink-0" />
          <p className="font-body text-white text-sm font-medium">
            Reconnecting… your progress is safe
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
