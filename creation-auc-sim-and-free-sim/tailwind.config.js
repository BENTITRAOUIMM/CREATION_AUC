/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class", // ✅ nécessaire pour useTheme
  content: [
    "./src/**/*.{js,jsx,ts,tsx}", // ✅ React
    "./public/index.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
