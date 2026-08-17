/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // The palette from the plan. stamp-red is reserved for overdue and destructive
        // actions — if it appears anywhere else, something has gone wrong.
        ink: '#161A1D',
        paper: '#F7F6F2',
        shelf: '#2F4A3F',
        stamp: '#9B2C2C',
        brass: '#B08D57',
        rule: '#D8D5CD',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        'reveal-up': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'reveal-up': 'reveal-up 320ms ease-out both',
      },
    },
  },
  plugins: [],
}
