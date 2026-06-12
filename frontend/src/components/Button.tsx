import { motion } from 'framer-motion';
import { ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg' | 'xl';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  className?: string;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    'bg-bobb-gold text-bobb-navy font-semibold hover:bg-yellow-400 active:bg-yellow-500',
  secondary:
    'bg-bobb-navy text-bobb-cream font-semibold hover:bg-blue-900 active:bg-blue-950 border border-bobb-navy',
  ghost:
    'bg-transparent text-bobb-navy font-medium hover:bg-bobb-navy/10 border border-bobb-navy/30',
  danger:
    'bg-red-600 text-white font-semibold hover:bg-red-700 active:bg-red-800',
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: 'px-4 py-2 text-sm rounded-button',
  md: 'px-6 py-3 text-base rounded-button',
  lg: 'px-8 py-4 text-lg rounded-button',
  xl: 'px-10 py-5 text-xl rounded-card',
};

export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  className = '',
}: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      disabled={disabled || loading}
      className={[
        'inline-flex items-center justify-center gap-2 transition-colors duration-150',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        fullWidth ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : null}
      {children}
    </motion.button>
  );
}
