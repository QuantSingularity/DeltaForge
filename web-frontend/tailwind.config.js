/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Instrument-panel neutrals (cool slate, never pure black)
        panel: {
          950: "#0a0e14",
          900: "#0f141c",
          850: "#141b26",
          800: "#1a2330",
          700: "#26303f",
          600: "#3a4759",
          500: "#5a6678",
        },
        ink: {
          DEFAULT: "#e6edf6",
          muted: "#8b97a8",
          faint: "#5a6678",
        },
        // Signature brand accent: forge ember
        ember: {
          DEFAULT: "#ff7a18",
          bright: "#ff9447",
          dim: "#b8530f",
        },
        // Trading semantics
        buy: "#26d07c",
        sell: "#ff4d5e",
        warn: "#f5b614",
        flat: "#4a5667",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "'SF Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel:
          "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
    },
  },
  plugins: [],
};
