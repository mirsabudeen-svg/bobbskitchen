import { ReactNode } from 'react';

interface ScreenShellProps {
  stateName: string;
  children?: ReactNode;
}

/** Sprint 0 placeholder shell — renders the state name with BOBB branding. */
export function ScreenShell({ stateName, children }: ScreenShellProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-bobb-cream">
      <h1 className="font-display text-5xl text-bobb-navy">BOBB</h1>
      <p className="rounded-card bg-bobb-navy px-8 py-4 font-body text-2xl text-bobb-gold">
        {stateName}
      </p>
      {children}
    </div>
  );
}
