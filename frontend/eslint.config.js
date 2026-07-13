import path from 'node:path';

import rotki from '@rotki/eslint-config';
import { translationKeys } from '@rotki/ui-library';

// Pre-load the ESM-only ESLint parsers before the config factories run.
// @intlify/eslint-plugin-vue-i18n require()s them while eslint composes configs
// via Promise.all; warming them here avoids Node's ERR_REQUIRE_ESM_RACE_CONDITION.
import 'jsonc-eslint-parser';
import 'yaml-eslint-parser';

const src = path.join('app', 'src');

// Keys referenced only through dynamic/computed lookups the static scanner cannot see, so they must
// not be reported as unused. `translationKeys()` covers the keys the ui-library resolves internally.
// Patterns are glob-ish: `*` is a wildcard, `.` is a literal dot (see the rule's `prepareUsedKeys`).
// Do NOT slash-wrap them like a regex literal - the rule treats the slashes as literal characters.
const i18nIgnoreKeys = [
  'backend_mappings.*',
  'notification_messages.missing_api_key.*',
  'premium_components.*',
  'transactions.query_status.*',
  'transactions.query_status_events.*',
  'transactions.events.headers.*',
  ...translationKeys(),
];

export default rotki({
  ignores: ['app/backend-icons.generated.ts', 'app/tests/e2e/test-results/**'],
  vue: true,
  typescript: {
    tsconfigPath: 'tsconfig.json',
  },
  stylistic: true,
  rotki: {
    src,
    ignoreKeys: i18nIgnoreKeys,
    overrides: {
      '@rotki/consistent-ref-type-annotation': ['error', {
        allowInference: true,
      }],
      '@rotki/no-dot-ts-imports': 'error',
    },
  },
  imports: {
    overrides: {
      '@rotki/max-dependencies': ['error', { max: 20 }],
    },
  },
  vueI18n: {
    src,
    overrides: {
      '@intlify/vue-i18n/no-i18n-t-path-prop': 'error',
      '@intlify/vue-i18n/no-deprecated-i18n-component': 'error',
      // Fail the build when a `t('...')` key is missing from the locale messages.
      '@intlify/vue-i18n/no-missing-keys': 'error',
    },
  },
}, {
  // `@rotki/no-unused-i18n-keys` only does work on locale files (it bails unless the linted file is
  // a locale JSON/YAML), but the config factory wires it to `.ts`/`.vue` globs only, so it never
  // runs. Apply it to every locale file so stale keys are caught in the translations too, not only
  // in the source `en.json`. `src`/`ignoreKeys` mirror the rotki block.
  files: ['**/locales/**/*.json', '**/locales/**/*.json5', '**/locales/**/*.{yaml,yml}'],
  rules: {
    '@rotki/no-unused-i18n-keys': ['error', {
      extensions: ['.ts', '.vue'],
      ignoreKeys: i18nIgnoreKeys,
      src,
    }],
  },
}, {
  files: ['**/*.ts', '**/*.vue'],
  rules: {
    '@typescript-eslint/consistent-type-assertions': ['warn', {
      assertionStyle: 'never',
    }],
  },
}, {
  files: ['**/src/**/*.ts'],
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
  },
}, {
  files: ['**/locales/**/*.json'],
  rules: {
    'jsonc/sort-keys': ['error', 'asc', {
      caseSensitive: true,
      natural: true,
    }],
  },
});
