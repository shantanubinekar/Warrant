/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Ink / paper — the instrument's neutral scale. Deliberately cool
        // (not warm cream), deliberately not pure black.
        ink: {
          DEFAULT: '#101B24',
          soft: '#3A4A56',
          faint: '#6B7A85',
        },
        paper: {
          DEFAULT: '#F3F5F4',
          raised: '#FFFFFF',
        },
        line: {
          DEFAULT: '#DDE3E1',
          strong: '#C3CBC9',
        },
        // Structural accent — used for interactive/brand elements only,
        // never for evidence signaling.
        signal: {
          DEFAULT: '#0E6E63',
          dark: '#0A5049',
          soft: '#E4F0EE',
        },
        // Evidence-state colors. Reserved ONLY for signaling the engine's
        // evidence state — never used decoratively elsewhere in the app.
        state: {
          good: { DEFAULT: '#1F7A4D', soft: '#E6F3EB', line: '#B9DCC5' },
          caution: { DEFAULT: '#A66A00', soft: '#FBF0DB', line: '#E9CD94' },
          critical: { DEFAULT: '#B3261E', soft: '#FAE7E5', line: '#E9B6B1' },
          neutral: { DEFAULT: '#3A4A56', soft: '#E7EBEC', line: '#C3CBC9' },
        },
      },
      fontFamily: {
        sans: ['"Public Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        // A single deliberate "instrument bezel" reserved for the one
        // bold element (the evidence-state reading) — not a default
        // shadow applied to every card.
        bezel: '0 1px 0 0 rgba(16,27,36,0.04), 0 1px 2px 0 rgba(16,27,36,0.06)',
      },
      borderRadius: {
        DEFAULT: '6px',
      },
    },
  },
  plugins: [],
}
