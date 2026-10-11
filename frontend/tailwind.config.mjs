/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
    darkMode: 'class',
    content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
    theme: {
      extend: {
        colors: {
          // Semantic tokens used by the ui/ primitives; values live in global.css per theme
          background: token('background'),
          foreground: token('foreground'),
          muted: { DEFAULT: token('muted'), foreground: token('muted-foreground') },
          card: { DEFAULT: token('card'), foreground: token('card-foreground') },
          accent: { DEFAULT: token('accent'), foreground: token('accent-foreground') },
          secondary: { DEFAULT: token('secondary'), foreground: token('secondary-foreground') },
          border: token('border'),
          input: token('input'),
          ring: token('ring'),
          primary: {
            DEFAULT: '#0369a1',
            50: '#f0f9ff',
            100: '#e0f2fe',
            500: '#0ea5e9',
            600: '#0284c7',
            700: '#0369a1',
            800: '#075985',
            900: '#0c4a6e',
          },
        },
      },
    },
    plugins: [],
  };
