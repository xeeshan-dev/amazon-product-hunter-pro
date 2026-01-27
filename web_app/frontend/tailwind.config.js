/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: {
                    bg: '#0F172A',
                    card: '#1E293B',
                    text: '#F8FAFC'
                },
                primary: {
                    DEFAULT: '#6366F1', // Indigo
                    hover: '#4F46E5',
                    glow: 'rgba(99, 102, 241, 0.5)'
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
