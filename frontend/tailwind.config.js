/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#10131A",
          card: "#171B24",
          raised: "#1F2430",
          line: "#2A2F3C",
        },
        paper: {
          DEFAULT: "#F2EFE9",
          dim: "#9AA1AE",
          faint: "#6B7280",
        },
        signal: {
          DEFAULT: "#E8A33D",
          bright: "#F4B85A",
          dim: "#8A6329",
        },
        tuned: {
          DEFAULT: "#6EE7B7",
          dim: "#3B8768",
        },
        flat: {
          DEFAULT: "#EF6461",
        },
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(232, 163, 61, 0.35)",
      },
    },
  },
  plugins: [],
};
