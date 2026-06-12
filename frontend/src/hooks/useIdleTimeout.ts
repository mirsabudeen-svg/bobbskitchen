import { useCallback, useEffect, useRef, useState } from 'react';

const INTERACTION_EVENTS = ['touchstart', 'touchmove', 'click', 'keydown', 'mousemove'] as const;

interface UseIdleTimeoutOptions {
  /** Total idle time before `onTimeout` fires (ms). Default: 3 min. */
  timeoutMs?: number;
  /** How long before timeout to show the warning overlay (ms). Default: 30s. */
  warningMs?: number;
  onTimeout: () => void;
  /** Only active when true — pass false during IDLE / PRODUCTION screens. */
  enabled: boolean;
}

interface UseIdleTimeoutResult {
  showWarning: boolean;
  secondsLeft: number;
  dismiss: () => void;
}

export function useIdleTimeout({
  timeoutMs = 3 * 60 * 1000,
  warningMs = 30 * 1000,
  onTimeout,
  enabled,
}: UseIdleTimeoutOptions): UseIdleTimeoutResult {
  const [showWarning, setShowWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const warnTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearAll = useCallback(() => {
    if (warnTimerRef.current) clearTimeout(warnTimerRef.current);
    if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
  }, []);

  const startCountdown = useCallback(() => {
    const secs = Math.round(warningMs / 1000);
    setSecondsLeft(secs);
    setShowWarning(true);
    countdownRef.current = setInterval(() => {
      setSecondsLeft((n) => Math.max(0, n - 1));
    }, 1000);
  }, [warningMs]);

  const arm = useCallback(() => {
    clearAll();
    setShowWarning(false);

    warnTimerRef.current = setTimeout(() => {
      startCountdown();
      resetTimerRef.current = setTimeout(() => {
        setShowWarning(false);
        onTimeout();
      }, warningMs);
    }, timeoutMs - warningMs);
  }, [clearAll, startCountdown, onTimeout, timeoutMs, warningMs]);

  const dismiss = useCallback(() => {
    arm();
  }, [arm]);

  useEffect(() => {
    if (!enabled) {
      clearAll();
      setShowWarning(false);
      return;
    }

    arm();

    const handleActivity = () => {
      if (!showWarning) arm();
    };

    INTERACTION_EVENTS.forEach((e) =>
      document.addEventListener(e, handleActivity, { passive: true }),
    );

    return () => {
      clearAll();
      INTERACTION_EVENTS.forEach((e) => document.removeEventListener(e, handleActivity));
    };
    // arm is stable; showWarning intentionally omitted so activity doesn't re-register listeners
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, arm]);

  return { showWarning, secondsLeft, dismiss };
}
