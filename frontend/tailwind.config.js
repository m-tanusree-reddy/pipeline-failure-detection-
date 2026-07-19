/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1440px",
      },
    },
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        border: "#2d3448",
        input: "#141b2d",
        ring: "#afc6ff",
        background: "#0c1324",
        foreground: "#dbe2fb",
        primary: {
          DEFAULT: "#afc6ff",
          foreground: "#002d6c",
          container: "#528dff",
        },
        secondary: {
          DEFAULT: "#d2bbff",
          foreground: "#3f008e",
        },
        destructive: {
          DEFAULT: "#ffb4ab",
          foreground: "#690005",
        },
        muted: {
          DEFAULT: "#181f31",
          foreground: "#c2c6d6",
        },
        accent: {
          DEFAULT: "#32394c",
          foreground: "#dbe2fb",
        },
        popover: {
          DEFAULT: "#181f31",
          foreground: "#dbe2fb",
        },
        card: {
          DEFAULT: "#141b2d",
          foreground: "#dbe2fb",
        },
      },
      borderRadius: {
        lg: "16px",
        md: "12px",
        sm: "8px",
        xl: "24px",
        full: "9999px"
      },
    },
  },
  plugins: [],
}
