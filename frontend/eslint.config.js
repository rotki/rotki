import path from 'node:path';

import rotki from '@rotki/eslint-config';
import { translationKeys } from '@rotki/ui-library';

import { backendMappingKeys } from './app/backend-strings.generated.js';
import { premiumComponentKeys } from './app/premium-keys.generated.js';
import { localRules } from './eslint-local-rules.js';

// vue-i18n require()s these while eslint composes configs; warming them avoids ERR_REQUIRE_ESM_RACE_CONDITION.
import 'jsonc-eslint-parser';
import 'yaml-eslint-parser';

const src = path.join('app', 'src');

/*
 * Keys reached only through computed lookups, which the scanner cannot see. Patterns are
 * glob-ish: `*` is a wildcard, `.` a literal dot. Do not slash-wrap them, the slashes are literal.
 */
const i18nIgnoreKeys = [
  /* Built at runtime from backend identifiers. Exact keys, not a glob: a glob hid
     `events.type.bridge` when it was renamed. Regenerate: `pnpm run generate:backend-strings`. */
  ...backendMappingKeys,
  /* Resolved by the premium bundle in another repo. Exact keys for the same reason: a glob hid 60
     retired ones. Regenerate: `pnpm run generate:premium-keys`. */
  ...premiumComponentKeys,
  ...translationKeys(),
];

export default rotki({
  /*
   * The gitignore integration reads only the root `.gitignore`, so what `app/.gitignore` hides
   * stays visible here. `.v8-coverage` matters most: megabytes of JSON that jsonc-eslint-parser
   * parses, turning a lint run into minutes. `**\/coverage` is already a shared-config default.
   */
  ignores: [
    'app/backend-icons.generated.ts',
    'app/backend-strings.generated.js',
    'app/premium-keys.generated.js',
    'app/src/route-map.d.ts',
    'app/tests/e2e/.v8-coverage/**',
    // A sharded run writes one output directory per shard: `test-results-1`, `-2`, ...
    'app/tests/e2e/test-results*/**',
    // The merged html report a sharded run leaves behind: a bundled trace viewer.
    'app/playwright-report/**',
  ],
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
  /* The shared config wires no-unused-i18n-keys to .ts/.vue globs, where the rule bails: it acts
     only on locale files. Pointed at them here so translations are checked, not just en.json. */
  files: ['**/locales/**/*.json', '**/locales/**/*.json5', '**/locales/**/*.{yaml,yml}'],
  rules: {
    '@rotki/no-unused-i18n-keys': ['error', {
      extensions: ['.ts', '.vue'],
      ignoreKeys: i18nIgnoreKeys,
      src,
    }],
  },
}, {
  /* Vite 8 loads configs natively and warns on extensionless relative imports, which
     `@rotki/no-dot-ts-imports` would autofix straight back off. Off for config files only. */
  files: ['**/vite.config.ts', '**/vite.config.*.ts', '**/vitest.config.ts', '**/vitest.*.config.ts'],
  rules: {
    '@rotki/no-dot-ts-imports': 'off',
  },
}, {
  files: ['**/src/**/*.ts'],
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
  },
}, {
  /*
   * A looser cap for presentational primitives, which are configured by many call sites; feature
   * components keep the project-wide cap, where a high prop count is a decomposition signal.
   * `settings/controls` counts as primitives: it imports nothing outside settings, shell and core.
   *
   * No file is exempted. Before exempting one, check `modules/premium/register-components.ts`:
   * those props are a public API for the separately released bundle. The cap is restated because
   * a flat config replaces a rule's options rather than merging them.
   */
  files: [
    '**/src/modules/shell/components/**/*.vue',
    '**/src/modules/assets/amount-display/**/*.vue',
    '**/src/modules/settings/controls/**/*.vue',
  ],
  rules: {
    'vue/max-props': ['error', { maxProps: 12 }],
  },
}, {
  /* Test ids are kebab-case; `__` is a Vuetify-era BEM leftover. A bound `:data-testid` is
     invisible to the rule, so keep it static and put anything variable on `data-key`. */
  files: ['**/*.vue'],
  rules: {
    'no-restricted-syntax': ['error', {
      // The object-literal form: `testId: 'a__b'` in a `<script setup>`.
      message: 'data-testid values are kebab-case; `__` is a BEM leftover.',
      selector: 'Property[key.name=/[Tt]est[Ii]d$/] > Literal[value=/__/]',
    }],
    'vue/no-restricted-static-attribute': ['error', {
      key: '/(^data-testid$|-test-id$)/',
      message: 'data-testid values are kebab-case. The BEM `__` separator is a Vuetify-era leftover.',
      value: '/__/',
    }, {
      // No `value`, so any use at all is an error.
      key: 'data-cy',
      message: 'Use `data-testid`. `data-cy` is a Cypress-era leftover.',
    }],
  },
}, {
  // The template rule cannot see a selector string in a page object, so e2e gets its own.
  files: ['**/tests/e2e/**/*.ts'],
  rules: {
    'no-restricted-syntax': ['error', {
      message: 'data-testid selectors are kebab-case; `__` is a BEM leftover.',
      selector: 'Literal[value=/data-testid[^_\\]]*__/]',
    }, {
      // `Literal` does not match a `TemplateLiteral`, and page objects build selectors that way.
      message: 'data-testid selectors are kebab-case; `__` is a BEM leftover.',
      selector: 'TemplateElement[value.raw=/data-testid[^_\\]]*__/]',
    }, {
      message: 'Query on `data-testid`. `data-cy` is a Cypress-era leftover.',
      selector: 'Literal[value=/data-cy/]',
    }, {
      message: 'Query on `data-testid`. `data-cy` is a Cypress-era leftover.',
      selector: 'TemplateElement[value.raw=/data-cy/]',
    }],
  },
}, {
  /* Coverage is armed on the `page` fixture in `tests/e2e/fixtures/test-fixtures.ts`. A spec that
     imports `test` from playwright still passes, it is just never counted. */
  files: ['**/tests/e2e/specs/**/*.ts'],
  rules: {
    'no-restricted-imports': ['error', {
      paths: [{
        importNames: ['test'],
        message: 'Import `test` from `tests/e2e/fixtures/test-fixtures`, which arms coverage on the page fixture.',
        name: '@playwright/test',
      }],
    }],
  },
}, {
  /*
   * main, preload and `shared/` are plain Node. Anything vue-shaped drags the vue runtime and its
   * compiler into a process that never renders: one `isDefined` from `@vueuse/core` cost the main
   * bundle 727 KB raw, 41% of it. Anchored to these two directories, not `**\/shared/**`, which
   * would also match `core/table/filters/shared` under `src/`.
   */
  files: ['app/electron/**/*.ts', 'app/shared/**/*.ts'],
  rules: {
    'no-restricted-imports': ['error', {
      /* Exact name, so `zod/mini` is untouched. Classic zod does not tree-shake: 421.9 KB against
         112.4 KB for mini, and one classic import anywhere in the graph brings all of it back. */
      paths: [{
        name: 'zod',
        message: 'Use `zod/mini` under electron/ and shared/. Classic zod costs the main bundle ~310 KB more.',
      }],
      patterns: [{
        group: ['vue', 'vue-*', '@vue/*', '@vueuse/*'],
        message: 'The electron main/preload bundles are plain Node. A vue or @vueuse import drags the vue runtime and compiler into them.',
      }],
    }],
  },
}, {
  /*
   * A real-clock sleep in a unit spec is a race: it passes on an idle laptop, fails on a loaded CI
   * box, and costs its full duration regardless. Use `vi.advanceTimersByTimeAsync()`,
   * `vi.waitUntil`/`vi.waitFor`, or a promise the test resolves itself.
   *
   * Only an *awaited* sleep is matched, in both spellings: `await wait(n)` from `@shared/utils`
   * and `await new Promise(resolve => setTimeout(resolve, n))`. Passing either as simulated work
   * inside a mock is untouched.
   */
  files: ['**/src/**/*.spec.ts', '**/shared/**/*.spec.ts', '**/electron/**/*.spec.ts'],
  rules: {
    'no-restricted-syntax': ['error', {
      message: 'Do not sleep on the real clock in a spec. Use fake timers (vi.advanceTimersByTimeAsync), poll a condition (vi.waitUntil/vi.waitFor), or resolve a promise the test controls.',
      selector: 'AwaitExpression > CallExpression[callee.name=\'wait\']',
    }, {
      message: 'Do not sleep on the real clock in a spec. Use fake timers (vi.advanceTimersByTimeAsync), poll a condition (vi.waitUntil/vi.waitFor), or resolve a promise the test controls.',
      selector: 'AwaitExpression > NewExpression[callee.name=\'Promise\']:has(CallExpression[callee.name=\'setTimeout\'])',
    }, {
      // Anchored on the `data-testid` prefix, so an id held in a bare constant stays review-only.
      message: 'data-testid selectors are kebab-case; `__` is a BEM leftover.',
      selector: 'Literal[value=/data-testid[^_\\]]*__/]',
    }, {
      message: 'data-testid selectors are kebab-case; `__` is a BEM leftover.',
      selector: 'TemplateElement[value.raw=/data-testid[^_\\]]*__/]',
    }, {
      message: 'Query on `data-testid`. `data-cy` is a Cypress-era leftover.',
      selector: 'Literal[value=/data-cy/]',
    }, {
      message: 'Query on `data-testid`. `data-cy` is a Cypress-era leftover.',
      selector: 'TemplateElement[value.raw=/data-cy/]',
    }],
  },
}, {
  files: ['app/src/**/*.ts', 'app/src/**/*.vue', 'common/src/**/*.ts'],
  plugins: {
    local: { rules: localRules },
  },
  rules: {
    'local/no-closure-result-in-activity-run': 'error',
  },
}, {
  // `events/composables.ts` keeps HistoryEventsView.vue under @rotki/max-dependencies.
  files: [
    'common/src/index.ts',
    'app/src/modules/assets/amount-display/index.ts',
    'app/src/modules/assets/amount-display/components/index.ts',
    'app/src/modules/core/messaging/types/index.ts',
    'app/src/modules/core/messaging/utils/index.ts',
    'app/src/modules/history/events/composables.ts',
  ],
  rules: {
    'unicorn/no-barrel-files': 'off',
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
