/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      boxShadow: {
        'glow': '0 0 10px rgba(0,0,0,0.1)'
      },
      backdropBlur: {
        xs: '2px'
      },
      transitionTimingFunction: {
        'elastic': 'cubic-bezier(0.68, -0.55, 0.27, 1.55)'
      }
    },
  },
  plugins: [],
}