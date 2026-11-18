/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A0B0D",
        foreground: "#F8FAFC",
        carbon: {
          bg: "#0A0B0D",
          card: "#111317",
          surface: "#16191F",
          elevated: "#1E222A",
          border: "rgba(255, 255, 255, 0.08)",
          "border-strong": "rgba(255, 255, 255, 0.16)",
          accent: "#38BDF8",
          emerald: "#10B981",
          amber: "#F59E0B",
          rose: "#F43F5E",
        },
        surface: {
          50: "#1E222A",
          100: "#181B22",
          200: "#14161C",
          300: "#111317",
          400: "#0D0E12",
        },
        brand: {
          50: "#F0F9FF",
          100: "#E0F2FE",
          500: "#38BDF8",
          600: "#0284C7",
          700: "#0369A1",
        },
        opus: {
          bg: "#0B0B10",
          card: "#121219",
          surface: "#181824",
          border: "#28243C",
          primary: "#7C3AED",
          violet: "#8B5CF6",
          emerald: "#10B981",
        },
        border: "rgba(255, 255, 255, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      boxShadow: {
        "carbon-card": "inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 4px 20px rgba(0, 0, 0, 0.5)",
        "carbon-glow": "0 0 25px -5px rgba(56, 189, 248, 0.15)",
      },
    },
  },
  plugins: [],
};
