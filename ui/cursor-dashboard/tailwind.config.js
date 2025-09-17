/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      animation: {
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%': { 
            filter: 'drop-shadow(0 0 5px rgba(255, 255, 255, 0.3)) drop-shadow(0 0 10px rgba(255, 255, 255, 0.2)) drop-shadow(0 0 15px rgba(255, 255, 255, 0.1))'
          },
          '50%': { 
            filter: 'drop-shadow(0 0 10px rgba(255, 255, 255, 0.6)) drop-shadow(0 0 20px rgba(255, 255, 255, 0.4)) drop-shadow(0 0 30px rgba(255, 255, 255, 0.2))'
          },
          '100%': { 
            filter: 'drop-shadow(0 0 5px rgba(255, 255, 255, 0.3)) drop-shadow(0 0 10px rgba(255, 255, 255, 0.2)) drop-shadow(0 0 15px rgba(255, 255, 255, 0.1))'
          },
        },
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // V0 Palette Anchor - exact hex values
        bg: {
          DEFAULT: '#0f0f10',
          tile: '#1a1a1a',
          tile2: '#1e1e1e',
          surface: '#212121',
          border: '#2a2a2a'
        },
        text: {
          primary: '#f9fafb',
          secondary: '#a1a1aa',
          muted: '#71717a'
        },
        brand: {
          primary: '#2563eb',
          primaryHover: '#1d4ed8'
        },
        status: {
          green: '#10b981',
          red: '#ef4444',
          amber: '#f59e0b'
        }
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
