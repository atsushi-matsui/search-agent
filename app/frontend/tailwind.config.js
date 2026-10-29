/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'page': '#f5f6f8',
        'surface': '#ffffff',
        'surface-muted': '#eceef2',
        'brand': '#e50914',
        'brand-hover': '#c40812',
      },
    },
  },
  plugins: [],
}
