/** @type {import('tailwindcss').Config} */
export default {
  // Tell Tailwind which files to scan for class names
  // It removes unused classes from the final CSS bundle (tree-shaking)
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      // Add custom design tokens here in later phases
      // e.g. colors, fonts, spacing, animations
    },
  },
  plugins: [],
}
