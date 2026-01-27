import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Banquise', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Consolas', 'monospace'],
      },
      colors: {
        // Grayscale palette
        gray: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d3d3d3',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
        // Coral accent (changes daily via CSS variable)
        coral: 'var(--accent-color)',
        'coral-light': 'var(--accent-color-light)',
      },
      boxShadow: {
        'hard-sm': '3px 3px 0 var(--shadow-color, #525252)',
        'hard': '4px 4px 0 var(--shadow-color, #525252)',
        'hard-lg': '6px 6px 0 var(--shadow-color, #404040)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
export default config
