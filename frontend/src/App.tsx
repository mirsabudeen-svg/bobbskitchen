import { AnimatePresence } from 'framer-motion';
import { useCallback, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useIdleTimeout } from './hooks/useIdleTimeout';
import { api } from './services/api';
import { useSessionStore } from './store/session';
import { SessionState } from './types';
import { ConnectionBanner } from './components/ConnectionBanner';
import { IdleWarningOverlay } from './components/IdleWarningOverlay';
import { SessionResumeOverlay } from './components/SessionResumeOverlay';
import { StaffPinGate } from './components/StaffPinGate';
import { StaffDashboard } from './screens/staff/StaffDashboard';
import { AnalyticsDashboard } from './screens/analytics/AnalyticsDashboard';
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
    <div className="min-h-screen bg-bobb-cream flex items-center justify-center px-8">
      <p className="font-display text-bobb-navy text-2xl text-center">
        Something went wrong. Please try again.
      </p>
    </div>
  ),
  [SessionState.HELP]: () => (
    <div className="min-h-screen bg-bobb-cream flex items-center justify-center px-8">
      <p className="font-display text-bobb-navy text-2xl text-center">
        Please ask a BOBB team member for help.
      </p>
    </div>
  ),
};

// States where idle timeout is active (i.e. a customer journey is in progress)
const IDLE_TIMEOUT_ACTIVE_STATES: SessionState[] = [
  SessionState.GREETING,
  SessionState.LISTENING,
  SessionState.CLARIFYING,
  SessionState.PREVIEW,
  SessionState.REFINING,
  SessionState.PRODUCT_SELECTION,
  SessionState.CART,
  SessionState.CHECKOUT,
  SessionState.SUCCESS,
];

export default function App() {
  // Staff interface served at /staff — PIN-protected, no customer state machine
  if (window.location.pathname === '/staff') {
    return (
      <StaffPinGate>
        <StaffDashboard />
      </StaffPinGate>
    );
  }

  // Analytics dashboard served at /analytics — PIN-protected
  if (window.location.pathname === '/analytics') {
    return (
      <StaffPinGate>
        <AnalyticsDashboard />
      </StaffPinGate>
    );
  }
  const sessionId = useSessionStore((s) => s.sessionId);
  const currentState = useSessionStore((s) => s.currentState);
  const pendingReconnect = useSessionStore((s) => s.pendingReconnect);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const setState = useSessionStore((s) => s.setState);
  const reset = useSessionStore((s) => s.reset);

  useWebSocket(sessionId);

  useEffect(() => {
    if (sessionId) return;
    api
      .createSession()
      .then((res) => {
        setSessionId(res.session_id);
        setState(res.state as SessionState);
      })
      .catch(() => {
        // Backend unreachable — stay on IDLE
      });
  }, [sessionId, setSessionId, setState]);

  const handleIdleTimeout = useCallback(() => {
    // Sprint 6.2 Fix 1: mark the abandoned session in the backend (fire-and-
    // forget), then fully reset — including sessionId — so the next customer
    // gets a brand-new session row (created by the effect above).
    const sid = useSessionStore.getState().sessionId;
    if (sid) void api.abandonSession(sid).catch(() => {});
    reset();
    setState(SessionState.IDLE);
  }, [reset, setState]);

  const { showWarning, secondsLeft, dismiss } = useIdleTimeout({
    onTimeout: handleIdleTimeout,
    enabled: IDLE_TIMEOUT_ACTIVE_STATES.includes(currentState),
  });

  const Screen = SCREENS[currentState] ?? SCREENS[SessionState.IDLE];

  return (
    <div className="min-h-screen overflow-hidden relative">
      <ConnectionBanner />

      <AnimatePresence mode="wait">
        <Screen key={currentState} />
      </AnimatePresence>

      {/* Session recovery interstitial — rendered above screen content */}
      <AnimatePresence>
        {pendingReconnect && <SessionResumeOverlay key="resume" />}
      </AnimatePresence>

      {/* Idle timeout warning — rendered at top z-level */}
      <AnimatePresence>
        {showWarning && !pendingReconnect && (
          <IdleWarningOverlay
            key="idle-warning"
            secondsLeft={secondsLeft}
            onDismiss={dismiss}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
