/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        toing: {
          purple: '#7C3AED',
          purpleDark: '#6D28D9',
          purpleLight: '#F3E8FF',
          purpleBg: '#FAF5FF',
          green: '#059669',
          greenLight: '#ECFDF5',
          greenBorder: '#A7F3D0',
          bg: '#F8FAFC',
          card: '#FFFFFF',
          textDark: '#0F172A',
          textMuted: '#64748B',
        },
        telegram: {
          bg: 'var(--tg-theme-bg-color, #ffffff)',
          text: 'var(--tg-theme-text-color, #0f172a)',
          hint: 'var(--tg-theme-hint-color, #64748b)',
          link: 'var(--tg-theme-link-color, #7c3aed)',
          button: 'var(--tg-theme-button-color, #7c3aed)',
          buttonText: 'var(--tg-theme-button-text-color, #ffffff)',
          secondaryBg: 'var(--tg-theme-secondary-bg-color, #f8fafc)'
        }
      },
      boxShadow: {
        'card': '0 2px 10px rgba(0, 0, 0, 0.03)',
        'float': '0 8px 30px rgba(124, 58, 237, 0.15)',
        'nav': '0 -4px 20px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
