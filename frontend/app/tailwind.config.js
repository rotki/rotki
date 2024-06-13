/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: 'jit',
  darkMode: 'class',
  content: [
    './src/components/**/*.vue',
    './src/layouts/**/*.vue',
    './src/pages/**/*.vue',
  ],
  theme: {
    container: {
      center: true,
    },
    extend: {},
  },
  // Classes for premium components
  safelist: ['!leading-7', 'lg:grid-cols-2', '-my-5', 'py-5', 'h-32'],
  plugins: [require('@rotki/ui-library-compat/theme')],
};
