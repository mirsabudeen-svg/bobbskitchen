import { useEffect, useState } from 'react';

const STAFF_PIN = import.meta.env.VITE_STAFF_PIN ?? '1234';
const SESSION_KEY = 'bobb_staff_auth';
const SESSION_TTL_MS = 8 * 60 * 60 * 1000; // 8 hours

interface Props {
  children: React.ReactNode;
}

export function StaffPinGate({ children }: Props) {
  const [authed, setAuthed] = useState(false);
  const [pin, setPin] = useState('');
  const [error, setError] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem(SESSION_KEY);
    if (stored) {
      try {
        const { expires } = JSON.parse(stored) as { expires: number };
        if (Date.now() < expires) setAuthed(true);
        else sessionStorage.removeItem(SESSION_KEY);
      } catch {
        sessionStorage.removeItem(SESSION_KEY);
      }
    }
  }, []);

  function handleSubmit() {
    if (pin === STAFF_PIN) {
      sessionStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ expires: Date.now() + SESSION_TTL_MS }),
      );
      setAuthed(true);
    } else {
      setError(true);
      setPin('');
      setTimeout(() => setError(false), 1500);
    }
  }

  if (authed) return <>{children}</>;

  return (
    <div className="min-h-screen bg-bobb-navy flex flex-col items-center justify-center gap-6 px-8">
      <div className="text-center mb-4">
        <p className="font-body text-bobb-gold text-xs uppercase tracking-widest mb-2">BOBB</p>
        <h1 className="font-display text-white text-3xl font-bold">Staff Access</h1>
      </div>
      <input
        type="password"
        inputMode="numeric"
        maxLength={6}
        value={pin}
        onChange={(e) => setPin(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        placeholder="Enter PIN"
        autoFocus
        className={[
          'w-48 text-center border-2 rounded-button px-5 py-4 font-display text-white text-2xl bg-white/10',
          'outline-none transition-colors placeholder-white/30 tracking-widest',
          error ? 'border-red-400' : 'border-white/20 focus:border-bobb-gold',
        ].join(' ')}
      />
      <button
        onClick={handleSubmit}
        className="bg-bobb-gold text-bobb-navy font-body font-semibold px-8 py-3 rounded-button hover:bg-bobb-gold/90 transition-colors"
      >
        Enter
      </button>
      {error && (
        <p className="font-body text-red-400 text-sm">Incorrect PIN</p>
      )}
    </div>
  );
}
