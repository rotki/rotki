import generated from '@rotki/ui-library/theme';

/** @type {import('tailwindcss').Config} */
export default {
  mode: 'jit',
  darkMode: 'class',
  content: ['./src/components/**/*.vue', './src/layouts/**/*.vue', './src/pages/**/*.vue'],
  theme: {
    container: {
      center: true,
    },
    fontFamily: {
      mono: ['Roboto Mono'],
    },
    extend: {},
  },
  // Classes for premium components
  safelist: ['!leading-7', 'lg:grid-cols-2', '-my-5', 'py-5', 'h-32'],
  plugins: [generated],
};
