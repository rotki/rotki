import path from 'node:path';

import rotki from '@rotki/eslint-config';
import { translationKeys } from '@rotki/ui-library';

import { backendMappingKeys } from './app/backend-strings.generated.js';
import { premiumComponentKeys } from './app/premium-keys.generated.js';

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
  // `backend_mappings.*` keys are built at runtime from identifiers the backend sends, so the
  // scanner cannot see them. Listing the exact keys rather than globbing the subtree means a key
  // the backend has stopped sending is still reported as unused - a blanket glob hid exactly that
  // when `events.type.bridge` was renamed to `events.group.bridge`. Regenerate with
  // `pnpm run generate:backend-strings`; `pnpm run check:backend-strings` fails when it is stale.
  ...backendMappingKeys,
  // The premium bundle lives in another repository and resolves its messages against ours, so these
  // keys have no usage here to find. Listed rather than globbed for the same reason as above: the
  // glob also hid 60 keys belonging to premium screens retired before the 14.x major.
  // `pnpm run generate:premium-keys` refreshes it from a premium checkout.
  ...premiumComponentKeys,
  ...translationKeys(),
];

export default rotki({
  // Test output directories are gitignored, but only by the nested `app/.gitignore`. The gitignore
  // integration reads just the root `.gitignore` next to this config, so it never sees those rules
  // and the generated files stay visible to eslint. `.v8-coverage` holds the Playwright V8 coverage
  // dumps, several megabytes of JSON that this config parses because it loads `jsonc-eslint-parser`,
  // which turns a full lint run into minutes. List them here instead. The vitest report directory
  // (`app/tests/unit/coverage`) is already covered by the shared config's `**/coverage` default.
  ignores: [
    'app/backend-icons.generated.ts',
    'app/backend-strings.generated.js',
    'app/premium-keys.generated.js',
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
  // Vite 8 loads the config file natively rather than bundling it, so a relative import without an
  // extension is a warning on every startup. `@rotki/no-dot-ts-imports` wants the opposite and would
  // autofix the extensions straight back off, so it is off for the config files themselves. It stays
  // on everywhere else, including the `scripts/` modules the config imports.
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
  // Low-level presentational primitives are legitimately knob-heavy: they exist to be configured by
  // many call sites, and every alternative reads worse (bundling props into synthetic objects hides
  // the component's real surface, and splitting a primitive just to duplicate its props buys
  // nothing). Feature and container components keep the stricter project-wide cap, so a high prop
  // count there stays a decomposition signal.
  // `settings/controls` qualifies on the same grounds: it imports nothing outside settings/shell/core,
  // so its components are generic setting widgets rather than feature-specific containers.
  //
  // No file is exempted from the cap any more. Before adding an exemption back, check whether the
  // component is registered in `modules/premium/register-components.ts`: those are rendered by the
  // separately released premium bundle, so their props are a public API for a consumer outside this
  // repo, and reshaping them needs the matching bundle change in the same release. Everything else
  // gets reshaped rather than exempted. Note that a cap has to be restated per group, because a flat
  // config replaces a rule's options rather than merging them.
  files: [
    '**/src/modules/shell/components/**/*.vue',
    '**/src/modules/assets/amount-display/**/*.vue',
    '**/src/modules/settings/controls/**/*.vue',
  ],
  rules: {
    'vue/max-props': ['error', { maxProps: 12 }],
  },
}, {
  // Test ids are kebab-case; `__` is a Vuetify-era BEM leftover. `key` is a regex, so the rule also
  // covers ids forwarded under a component's own `*-test-id` attribute. A bound `:data-testid` is
  // invisible to all of this: keep the attribute static and put anything variable on `data-key`.
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
  // The template rule cannot see a selector string in a page object, so the e2e side gets its own.
  // A flat config replaces a rule's options rather than merging them, so specs join the
  // `no-restricted-syntax` array further down instead of getting a block of their own.
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
  // Coverage is armed on the `page` fixture in `tests/e2e/fixtures/test-fixtures`, so a spec that
  // takes `test` straight from playwright silently contributes nothing to the coverage report.
  // That failure is invisible - the spec passes, it is just never counted - so it is worth a rule
  // rather than a convention. `expect` and the types are unaffected.
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
  // The electron main and preload bundles are plain Node, and `shared/` is compiled into them.
  // Importing anything vue-shaped there pulls the vue runtime *and* its compiler (via
  // @vue/compiler-core -> @babel/parser) into a process that never renders: one `isDefined` from
  // @vueuse/core cost the main bundle 727 KB raw, 41% of it. Reach for a plain helper instead.
  // Anchored to the two real directories rather than `**/shared/**`, which also matches any folder
  // named `shared` under `src/` (for example `core/table/filters/shared`), where vue is expected.
  files: ['app/electron/**/*.ts', 'app/shared/**/*.ts'],
  rules: {
    'no-restricted-imports': ['error', {
      // Matched by exact name, so `zod/mini` itself is untouched. Classic zod does not tree-shake:
      // its chained methods keep the whole surface reachable, and it measured 421.9 KB here against
      // 112.4 KB for mini. One classic import anywhere in this graph brings all of it back.
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
  // Unit specs must never wait on the real clock. A fixed sleep is a race, not a wait: it passes on an
  // idle laptop and fails on a loaded CI box, and it costs its full duration even when the work it
  // waits for finished immediately. Use what vitest gives you instead - `vi.useFakeTimers()` plus
  // `vi.advanceTimersByTimeAsync()` to drive a debounce or interval, `vi.waitUntil`/`vi.waitFor` to poll
  // a condition, or a promise the test resolves itself to hold an async call open.
  //
  // Both selectors target *awaiting* a sleep, which is the only form that stalls a test:
  // - `await wait(50)` - the real-clock sleep from `@shared/utils`. Under fake timers this deadlocks
  //   anyway, so it is always wrong at test level. Passing `wait` as simulated work (`async () =>
  //   wait(1500)`) or asserting on it when mocked is untouched, since neither is awaited here.
  // - `await new Promise(resolve => setTimeout(resolve, n))` - the same sleep spelled out. Scheduling a
  //   `setTimeout` inside a mock that fake timers then advance is untouched for the same reason.
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
  files: ['**/locales/**/*.json'],
  rules: {
    'jsonc/sort-keys': ['error', 'asc', {
      caseSensitive: true,
      natural: true,
    }],
  },
});
