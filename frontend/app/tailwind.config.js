/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: 'jit',
  darkMode: 'class',
  content: [
    './src/components/**/*.vue',
    './src/layouts/**/*.vue',
    './src/pages/**/*.vue'
  ],
  theme: {
    extend: {}
  },
  safelist: ['!leading-7', 'lg:grid-cols-2'],
  plugins: [require('@rotki/ui-library-compat/theme')]
};
