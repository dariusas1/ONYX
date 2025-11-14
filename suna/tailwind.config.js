/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        manus: {
          bg: '#0F172A',        // Deep navy background
          surface: '#1E293B',   // Elevated surface
          accent: '#2563EB',    // Primary blue
          text: '#E2E8F0',      // Light gray text
          muted: '#64748B',     // Muted text
          border: '#334155',    // Border color
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      maxWidth: {
        'chat': '900px',  // Maximum content width for chat interface
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
