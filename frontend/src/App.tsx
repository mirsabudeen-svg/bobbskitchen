import { AnimatePresence } from 'framer-motion';
import { useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './services/api';
import { useSessionStore } from './store/session';
import { SessionState } from './types';
import { IdleScreen } from './screens/IdleScreen';
import { GreetingScreen } from './screens/GreetingScreen';
import { ListeningScreen } from './screens/ListeningScreen';
import { ClarifyingScreen } from './screens/ClarifyingScreen';
import { ThinkingScreen } from './screens/ThinkingScreen';
import { GeneratingScreen } from './screens/GeneratingScreen';
import { PreviewScreen } from './screens/PreviewScreen';
import { RefiningScreen } from './screens/RefiningScreen';
import { ProductSelectionScreen } from './screens/ProductSelectionScreen';
import { CartScreen } from './screens/CartScreen';
import { CheckoutScreen } from './screens/CheckoutScreen';
import { ProductionScreen } from './screens/ProductionScreen';
import { SuccessScreen } from './screens/SuccessScreen';

const SCREENS: Record<SessionState, () => JSX.Element | null> = {
  [SessionState.IDLE]: IdleScreen,
  [SessionState.GREETING]: GreetingScreen,
  [SessionState.LISTENING]: ListeningScreen,
  [SessionState.CLARIFYING]: ClarifyingScreen,
  [SessionState.THINKING]: ThinkingScreen,
  [SessionState.GENERATING]: GeneratingScreen,
  [SessionState.PREVIEW]: PreviewScreen,
  [SessionState.REFINING]: RefiningScreen,
  [SessionState.PRODUCT_SELECTION]: ProductSelectionScreen,
  [SessionState.CART]: CartScreen,
  [SessionState.CHECKOUT]: CheckoutScreen,
  [SessionState.PRODUCTION]: ProductionScreen,
  [SessionState.SUCCESS]: SuccessScreen,
  [SessionState.ERROR]: () => (
    <div className="min-h-screen bg-bobb-cream flex items-center justify-center">
      <p className="font-display text-bobb-navy text-2xl">Something went wrong. Please try again.</p>
    </div>
  ),
  [SessionState.HELP]: () => (
    <div className="min-h-screen bg-bobb-cream flex items-center justify-center">
      <p className="font-display text-bobb-navy text-2xl">Please ask a BOBB team member for help.</p>
    </div>
  ),
};

export default function App() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const currentState = useSessionStore((s) => s.currentState);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const setState = useSessionStore((s) => s.setState);

  useWebSocket(sessionId);

  useEffect(() => {
    if (sessionId) return;
    api
      .createSession()
      .then((res) => {
        setSessionId(res.session_id);
        // createSession returns state='greeting'; keep the store in sync
        setState(res.state as SessionState);
      })
      .catch(() => {
        // Backend unreachable — stay on IDLE
      });
  }, [sessionId, setSessionId, setState]);

  const Screen = SCREENS[currentState] ?? SCREENS[SessionState.IDLE];

  return (
    <div className="min-h-screen overflow-hidden relative">
      <AnimatePresence mode="wait">
        <Screen key={currentState} />
      </AnimatePresence>
    </div>
  );
}
