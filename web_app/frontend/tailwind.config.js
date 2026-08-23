/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // ── Surface layer (layered depth, not one flat hue) ──
                ink: {
                    950: '#05080F',   // app background, deepest
                    900: '#0A0F1C',   // page sections
                    850: '#0D1424',
                    800: '#111A2E',   // raised panels
                    700: '#1A2440',   // hover / raised-2
                },
                surface: {
                    DEFAULT: '#101828',
                    raised: '#16203A',
                    overlay: '#1C2745',
                },
                line: 'rgba(148,163,184,0.12)',
                // ── Brand ──
                brand: {
                    50: '#EEF2FF',
                    100: '#E0E7FF',
                    200: '#C7D2FE',
                    300: '#A5B4FC',
                    400: '#818CF8',
                    500: '#6366F1',
                    600: '#5457E8',
                    700: '#4649C6',
                },
                // ── Opportunity gold (analytics-dashboard accent per ui-ux-pro-max) ──
                gold: {
                    300: '#FCD34D',
                    400: '#FBBF24',
                    500: '#F59E0B',
                    600: '#D97706',
                },
                primary: {
                    DEFAULT: '#6366F1',
                    hover: '#5457E8',
                    glow: 'rgba(99, 102, 241, 0.45)',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
                mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
            },
            boxShadow: {
                // Elevation scale — consistent, never random values
                elev1: '0 1px 2px rgba(2,6,23,.35), 0 0 0 1px rgba(148,163,184,.06)',
                elev2: '0 8px 24px -8px rgba(2,6,23,.55), 0 0 0 1px rgba(148,163,184,.08)',
                elev3: '0 20px 50px -16px rgba(2,6,23,.65), 0 0 0 1px rgba(148,163,184,.10)',
                'glow-brand': '0 0 0 1px rgba(99,102,241,.35), 0 8px 32px -8px rgba(99,102,241,.45)',
            },
            backgroundImage: {
                'brand-gradient': 'linear-gradient(135deg,#818CF8 0%,#6366F1 45%,#22D3EE 100%)',
                'gold-gradient': 'linear-gradient(135deg,#FCD34D 0%,#F59E0B 100%)',
            },
        },
    },
    plugins: [],
}
