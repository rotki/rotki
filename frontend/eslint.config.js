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
  // Test output directories are gitignored, but only by the nested `app/.gitignore`. The gitignore
  // integration reads just the root `.gitignore` next to this config, so it never sees those rules
  // and the generated files stay visible to eslint. `.v8-coverage` holds the Playwright V8 coverage
  // dumps, several megabytes of JSON that this config parses because it loads `jsonc-eslint-parser`,
  // which turns a full lint run into minutes. List them here instead. The vitest report directory
  // (`app/tests/unit/coverage`) is already covered by the shared config's `**/coverage` default.
  ignores: [
    'app/backend-icons.generated.ts',
    'app/tests/e2e/.v8-coverage/**',
    'app/tests/e2e/test-results/**',
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
  files: [
    '**/src/modules/shell/components/**/*.vue',
    '**/src/modules/assets/amount-display/**/*.vue',
    '**/src/modules/settings/controls/**/*.vue',
  ],
  rules: {
    'vue/max-props': ['error', { maxProps: 12 }],
  },
}, {
  // `modules/premium/register-components.ts` registers 27 of our components globally so the
  // separately released premium bundle can render them. Their props are therefore a public API for a
  // consumer that does not live in this repo: renaming or grouping them cannot be verified here and
  // would break premium at runtime with nothing in our lint, typecheck or test suite noticing.
  //
  // These four exceed their cap and cannot be fixed unilaterally, so the rule is downgraded rather
  // than silenced: the count stays reported, and reducing it needs a coordinated premium release.
  // Caps are restated per group because a flat config replaces a rule's options rather than merging
  // them, and dropping the cap here would stop the warning firing at all.
  //
  // If another registered component crosses its cap, add it here rather than reshaping its props.
  files: [
    '**/src/modules/history/events/HistoryEventsView.vue',
    '**/src/modules/accounts/BlockchainAccountSelector.vue',
    '**/src/modules/assets/AssetDetails.vue',
  ],
  rules: {
    'vue/max-props': ['warn', { maxProps: 8 }],
  },
}, {
  // Registered too, but under the relaxed primitive cap above, so it keeps 12 and only warns.
  files: ['**/src/modules/shell/components/inputs/AssetSelect.vue'],
  rules: {
    'vue/max-props': ['warn', { maxProps: 12 }],
  },
}, {
  // A DIFFERENT GROUP from the premium-registered files above: these are internal, so their props
  // can be reshaped in this repo. They are warnings only because the work is outstanding, not because
  // it is blocked, and each one has a known route:
  //
  // - BigDialog (16): primaryAction/actionDisabled/actionTooltip/actionHidden are one action, and
  //   errorCount/autoScrollToError are one error concern. 4+2 props become 2, landing exactly on 12.
  //   Held up only by its 28 call sites.
  // - AppImage (13): `contain` and `cover` are mutually exclusive object-fit modes and want to be one
  //   `fit` prop. One prop to shed, but 31 files pass one of the two.
  files: [
    '**/src/modules/shell/components/dialogs/BigDialog.vue',
    '**/src/modules/shell/components/AppImage.vue',
  ],
  rules: {
    'vue/max-props': ['warn', { maxProps: 12 }],
  },
}, {
  // Same group as BigDialog/AppImage above (internal, fixable here), at the stricter default cap:
  //
  // - ServiceKeyCard (12): primaryAction/actionDisabled/hideAction/addButtonText/editButtonText are
  //   all one action; 5 props become 1, which lands exactly on 8.
  // - HistoryEventNote (9): every prop it takes is derived from `event` plus useHistoryEventItem, so
  //   it could take the event instead. Gated on whether all six callers actually hold a
  //   HistoryEventEntry: ProfitLossEvents and TradeHistoryItem look like they do not.
  // - AssetDetailsBase (12), AssetBalances (11): display flags that are genuinely independent, so no
  //   honest grouping exists. These need real decomposition. Note AssetDetailsBase is the inner
  //   component, free to change; its AssetDetails wrapper is premium-registered and frozen.
  // - HistoryEventsDetailItem (9): already reduced from 10, and the rest are independent
  //   (groupLocationLabel and matchedMovement are unrelated in both this component and
  //   HistoryEventType; `index` carries swap sub-event ordering). Fold into the facade work below.
  // - HistoryEventsVirtualTable (14): deferred to the facade redesign, which also owns its 8
  //   max-template-depth errors and its 20/20 @rotki/max-dependencies ceiling.
  files: [
    '**/src/modules/settings/api-keys/ServiceKeyCard.vue',
    '**/src/modules/history/events/HistoryEventNote.vue',
    '**/src/modules/assets/AssetDetailsBase.vue',
    '**/src/modules/balances/AssetBalances.vue',
    '**/src/modules/history/events/components/HistoryEventsDetailItem.vue',
    '**/src/modules/history/events/components/HistoryEventsVirtualTable.vue',
  ],
  rules: {
    'vue/max-props': ['warn', { maxProps: 8 }],
  },
}, {
  // HistoryEventsVirtualTable's remaining depth comes from the row markup it hosts inline. Extracting
  // that markup needs one more import and the file already sits at the @rotki/max-dependencies ceiling
  // of 20, so the fix is the facade redesign that also owns its prop count, not a local change. Warn
  // rather than block until that lands.
  files: ['**/src/modules/history/events/components/HistoryEventsVirtualTable.vue'],
  rules: {
    'vue/max-template-depth': 'warn',
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
  files: ['**/locales/**/*.json'],
  rules: {
    'jsonc/sort-keys': ['error', 'asc', {
      caseSensitive: true,
      natural: true,
    }],
  },
});
