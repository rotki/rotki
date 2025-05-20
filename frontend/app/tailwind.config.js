import generated from '@rotki/ui-library/theme';
import plugin from 'tailwindcss/plugin';

const containerQueryPlugin = plugin(
  ({ matchUtilities, matchVariant, theme }) => {
    const values = theme('containers') ?? {};

    function parseValue(value) {
      const numericValue = value.match(/^(\d+\.\d+|\d+|\.\d+)\D+/)?.[1] ?? null;
      if (numericValue === null)
        return null;

      return parseFloat(value);
    }

    matchUtilities(
      {
        '@container': (value, { modifier }) => ({
          'container-name': modifier,
          'container-type': value,
        }),
      },
      {
        modifiers: 'any',
        values: {
          DEFAULT: 'inline-size',
          normal: 'normal',
        },
      },
    );

    matchVariant(
      '@',
      (value = '', { modifier }) => {
        const parsed = parseValue(value);

        return parsed !== null ? `@container ${modifier ?? ''} (min-width: ${value})` : [];
      },
      {
        sort(aVariant, zVariant) {
          const a = parseFloat(aVariant.value);
          const z = parseFloat(zVariant.value);

          if (a === null || z === null)
            return 0;

          // Sort values themselves regardless of unit
          if (a - z !== 0)
            return a - z;

          const aLabel = aVariant.modifier ?? '';
          const zLabel = zVariant.modifier ?? '';

          // Explicitly move empty labels to the end
          if (aLabel === '' && zLabel !== '') {
            return 1;
          }
          else if (aLabel !== '' && zLabel === '') {
            return -1;
          }

          // Sort labels alphabetically in the English locale
          // We are intentionally overriding the locale because we do not want the sort to
          // be affected by the machine's locale (be it a developer or CI environment)
          return aLabel.localeCompare(zLabel, 'en', { numeric: true });
        },
        values,
      },
    );
  },
  {
    theme: {
      containers: {
        '2xl': '42rem',
        '3xl': '48rem',
        '4xl': '56rem',
        '5xl': '64rem',
        '6xl': '72rem',
        '7xl': '80rem',
        'lg': '32rem',
        'md': '28rem',
        'sm': '24rem',
        'xl': '36rem',
        'xs': '20rem',
      },
    },
  },
);

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
    'h-[30rem]',
  ],
  plugins: [generated, containerQueryPlugin],
};
