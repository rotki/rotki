import type { Config } from 'tailwindcss';
import type { PluginAPI } from 'tailwindcss/types/config';
import generated from '@rotki/ui-library/theme';
import plugin from 'tailwindcss/plugin';

interface VariantValue {
  value: string;
  modifier: string | null;
}

const componentsPlugin = plugin((pluginAPI: PluginAPI) => {
  pluginAPI.addBase({
    'html': {
      '@apply overflow-y-hidden max-h-screen antialiased': {},
    },
    'body': {
      '@apply transition-all bg-rui-grey-50 dark:bg-[#121212] overflow-x-hidden h-[calc(100vh-4rem)] scroll-smooth scroll-pt-16 mt-16 overflow-y-auto': {},
      '--w3m-z-index': '10000',
    },
    '@media only screen and (max-width: 767px)': {
      body: {
        '@apply h-[calc(100vh-3.5rem)] mt-14': {},
      },
    },
    'aside': {
      '@apply max-w-[100vw] !top-[3.5rem] md:!top-[4rem] max-h-[calc(100vh-3.5rem)] md:max-h-[calc(100vh-4rem)]': {},
    },
    'input::-webkit-outer-spin-button, input::-webkit-inner-spin-button': {
      '@apply appearance-none': {},
    },
    'input[type="number"]': {
      '-moz-appearance': 'textfield',
    },
    'ul, ol': {
      '@apply pl-6': {},
    },
    'a': {
      '@apply cursor-pointer text-rui-blue-800 dark:text-rui-blue-600': {},
    },
  });
  pluginAPI.addComponents({
    '.skeleton': {
      '@apply animate-pulse bg-gray-200 dark:bg-gray-800': {},
    },
    '.icon-bg': {
      '@apply dark:rounded-md dark:bg-rui-grey-100 p-0.5': {},
    },
    '.container': {
      '@apply px-4': {},
      'maxWidth': '1500px',
    },
    '.table-inside-dialog': {
      '@apply scroll-smooth overflow-auto': {},
      'maxHeight': 'calc(100vh - 21.25rem)',
    },
  });
  pluginAPI.addUtilities({
    '.blur': {
      filter: 'blur(0.75em)',
    },
    '.break-words': {
      wordBreak: 'break-word',
    },
    '.text-truncate': {
      whiteSpace: 'nowrap !important',
      overflow: 'hidden !important',
      textOverflow: 'ellipsis !important',
    },
  });
});

const containerQueryPlugin = plugin((pluginAPI: PluginAPI) => {
  const values = pluginAPI.theme('containers') ?? {};

  function parseValue(value: string): number | null {
    const numericValue = value.match(/^(\d+\.\d+|\d+|\.\d+)\D+/)?.[1] ?? null;
    if (numericValue === null)
      return null;

    return Number.parseFloat(value);
  }

  pluginAPI.matchUtilities({
    '@container': (value: string, { modifier }: { modifier: string | null }) => ({
      'container-name': modifier,
      'container-type': value,
    }),
  }, {
    modifiers: 'any',
    values: {
      DEFAULT: 'inline-size',
      normal: 'normal',
    },
  });

  pluginAPI.matchVariant('@', (value = '', { modifier }: { modifier: string | null }) => {
    const parsed = parseValue(value);

    return parsed !== null ? `@container ${modifier ?? ''} (min-width: ${value})` : [];
  }, {
    sort(aVariant: VariantValue, zVariant: VariantValue) {
      const a = Number.parseFloat(aVariant.value);
      const z = Number.parseFloat(zVariant.value);

      if (Number.isNaN(a) || Number.isNaN(z))
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
  });
}, {
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
});

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
    extend: {
      keyframes: {
        'shake': {
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
        'pulse-highlight': {
          '0%, 100%': { backgroundColor: 'rgba(202, 138, 4, 0)' },
          '50%': { backgroundColor: 'rgba(202, 138, 4, 0.3)' },
        },
      },
      animation: {
        'shake': 'shake 0.5s ease-in-out',
        'pulse-highlight': 'pulse-highlight 1.5s ease-in-out infinite',
      },
    },
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
  plugins: [generated, componentsPlugin, containerQueryPlugin],
} satisfies Config;
