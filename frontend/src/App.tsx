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
import { ScreenShell } from './components/ScreenShell';

const SCREENS: Record<SessionState, () => JSX.Element> = {
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
  [SessionState.ERROR]: () => <ScreenShell stateName="ERROR" />,
  [SessionState.HELP]: () => <ScreenShell stateName="HELP" />,
};

export default function App() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const currentState = useSessionStore((s) => s.currentState);
  const setSessionId = useSessionStore((s) => s.setSessionId);

  useWebSocket(sessionId);

  useEffect(() => {
    if (sessionId) return;
    api
      .createSession()
      .then((res) => setSessionId(res.session_id))
      .catch(() => {
        // Backend unreachable — stay on IDLE; reconnect handled later sprints.
      });
  }, [sessionId, setSessionId]);

  const Screen = SCREENS[currentState] ?? SCREENS[SessionState.IDLE];
  return <Screen />;
}
