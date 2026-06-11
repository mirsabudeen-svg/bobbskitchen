/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // BOBB brand design tokens (architecture.md)
        'bobb-gold': '#E8C547',
        'bobb-navy': '#0A1A3F',
        'bobb-cream': '#FAF7F0',
        'bobb-saffron': '#E8833A',
        'bobb-green': '#2D6A4F',
      },
      fontFamily: {
        display: ['"Playfair Display"', 'serif'],
        body: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        button: '12px',
      },
    },
  },
  plugins: [],
};
