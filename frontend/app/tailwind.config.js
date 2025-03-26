import generated from '@rotki/ui-library/theme';

/** @type {import('tailwindcss').Config} */
export default {
  mode: 'jit',
  darkMode: 'class',
  content: [
    './src/components/**/*.vue',
    './src/layouts/**/*.vue',
    './src/modules/**/*.vue',
    './src/pages/**/*.vue',
  ],
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
  safelist: [
    '!leading-7',
    'lg:grid-cols-2',
    '-my-5',
    'py-5',
    'h-32',
    'lg:grid-cols-5',
    'lg:col-span-3',
    'lg:col-span-2',
    'pl-6',
    '[&_span]:!text-xs',
    '!text-center',
    '[&>div>div>div]:font-normal',
    'bg-white/[0.9]',
    'dark:bg-[#1E1E1E]/[0.9]',
    'list-decimal',
    '!leading-4',
    'lg:col-span-2',
    'min-h-[560px]',
    '!pt-0',
  ],
  plugins: [generated],
};
