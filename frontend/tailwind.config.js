/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body:    ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono:    ['"IBM Plex Mono"', 'Consolas', 'monospace'],
      },
      colors: {
        slate: {
          950: '#0a0f1e',
          900: '#0f172a',
          850: '#131f35',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
          400: '#94a3b8',
          300: '#cbd5e1',
          200: '#e2e8f0',
          100: '#f1f5f9',
        },
        amber: {
          500: '#f59e0b',
          400: '#fbbf24',
          300: '#fcd34d',
          200: '#fde68a',
        },
        emerald: { 500: '#10b981', 400: '#34d399', 300: '#6ee7b7' },
        rose:    { 500: '#f43f5e', 400: '#fb7185', 300: '#fda4af' },
        sky:     { 500: '#0ea5e9', 400: '#38bdf8', 300: '#7dd3fc' },
      },
      animation: {
        'fade-up':   'fadeUp 0.4s ease forwards',
        'fade-in':   'fadeIn 0.3s ease forwards',
        'pulse-slow':'pulse 3s ease-in-out infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        fadeUp: {
          '0%':   { opacity: 0, transform: 'translateY(16px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: 0 },
          '100%': { opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}