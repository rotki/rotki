<script setup lang="ts">
import { type McpPrivacyMode, McpPrivacyMode as PrivacyMode } from '@/modules/settings/types/mcp';

const { mode } = defineProps<{
  mode: McpPrivacyMode;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * A single cell. `plain` reaches the assistant verbatim, `hash` is the session-stable `anon_`
 * identifier, and `redacted` is free text replaced by a `has_<field>` flag.
 *
 * The two empty states are not the same and must not render alike: `undefined` means this event
 * carried no such value while the column still exists (another event fills it, so the assistant
 * reads null), whereas `absent` means the mode emits no such column at all and querying it fails.
 */
type PreviewValue =
  | { readonly kind: 'plain'; readonly text: string; readonly flag?: string }
  | { readonly kind: 'hash'; readonly text: string }
  | { readonly kind: 'redacted'; readonly text: string; readonly flag: string }
  | { readonly kind: 'absent' };

interface PreviewRow {
  readonly field: string;
  readonly deposit?: PreviewValue;
  readonly swap?: PreviewValue;
}

function plain(text: string): PreviewValue {
  return { kind: 'plain', text };
}

// A text column always ships its `has_<column>` companion, whatever the mode leaves in the column
// itself. Not translated: these are literal values the assistant receives, not prose.
function flagged(text: string, field: string): PreviewValue {
  return { flag: `has_${field}: true`, kind: 'plain', text };
}

function hash(text: string): PreviewValue {
  return { kind: 'hash', text };
}

function absent(): PreviewValue {
  return { kind: 'absent' };
}

function redacted(field: string): PreviewValue {
  return { flag: `has_${field}: true`, kind: 'redacted', text: '[redacted]' };
}

// The sample values below mirror `_sanitize_row` in rotkehlchen/mcp/analytics.py. Keep them in
// step with it: `GENERATED_TEXT_COLUMN_NAMES` decides whether `auto_notes` survives balanced, and
// `READABLE_LOCATION_LABELS` decides which `location_label` values stay readable there (only a
// value that is exactly a rotki location name -- a user-assigned account name is hashed).
const commonRows: PreviewRow[] = [
  { deposit: plain('1754425840000'), field: 'timestamp', swap: plain('1754431200000') },
  { deposit: plain('kraken'), field: 'location', swap: plain('ethereum') },
  { deposit: plain('deposit'), field: 'event_type', swap: plain('trade') },
  { deposit: plain('BTC'), field: 'asset', swap: plain('ETH') },
  { deposit: plain('0.4'), field: 'amount', swap: plain('1.25') },
  { field: 'counterparty', swap: plain('uniswap-v3') },
];

/**
 * Builds the rows whose shape the chosen privacy mode decides.
 *
 * @remarks
 * Raw is the only mode where an identifier keeps its own column name. Everywhere else the value
 * moves to `<column>_hash` and the original column is dropped, with one exception: under balanced,
 * a venue-name label also stays readable under `location_label`.
 */
const modeRows = computed<PreviewRow[]>(() => {
  if (mode === PrivacyMode.RAW) {
    return [
      { deposit: plain('kraken'), field: 'location_label', swap: plain('0x9C5083…5dAC5') },
      { field: 'tx_hash', swap: plain('0x3f1a…9d2c') },
      {
        deposit: plain('Deposit 0.4 BTC to Kraken'),
        field: 'auto_notes',
        swap: plain('Swap 1.25 ETH for 4381.25 USDC'),
      },
      { field: 'user_notes', swap: plain('quarterly rebalance') },
    ];
  }

  if (mode === PrivacyMode.BALANCED) {
    return [
      {
        deposit: hash('anon_b43a5d4cd838add9'),
        field: 'location_label_hash',
        swap: hash('anon_5c4efe77c7146ef8'),
      },
      { deposit: plain('kraken'), field: 'location_label' },
      { field: 'tx_hash_hash', swap: hash('anon_61b73c8e638bc34c') },
      {
        deposit: flagged('Deposit 0.4 BTC to Kraken', 'auto_notes'),
        field: 'auto_notes',
        swap: flagged('Swap 1.25 ETH for 4381.25 USDC', 'auto_notes'),
      },
      { field: 'user_notes', swap: redacted('user_notes') },
    ];
  }

  return [
    {
      deposit: hash('anon_b43a5d4cd838add9'),
      field: 'location_label_hash',
      swap: hash('anon_5c4efe77c7146ef8'),
    },
    // Strict emits no readable label column at all. The row stays so switching to balanced does not
    // reflow the table, but it says "not sent" rather than "not set": querying it would fail.
    { deposit: absent(), field: 'location_label', swap: absent() },
    { field: 'tx_hash_hash', swap: hash('anon_61b73c8e638bc34c') },
    { deposit: redacted('auto_notes'), field: 'auto_notes', swap: redacted('auto_notes') },
    { field: 'user_notes', swap: redacted('user_notes') },
  ];
});

/** A row flattened to the column order the table renders, so each cell binds to a narrowable alias. */
interface PreviewLine {
  readonly field: string;
  readonly cells: readonly (PreviewValue | undefined)[];
}

function toLines(rows: PreviewRow[]): PreviewLine[] {
  return rows.map(({ deposit, field, swap }) => ({ cells: [swap, deposit], field }));
}

// The split is the point: the first group is what every mode sends, the second is what the chosen
// mode decides.
const groups = computed<{ label: string; lines: PreviewLine[] }[]>(() => [
  {
    label: t('backend_settings.settings.mcp_server.privacy_mode.preview.group_always'),
    lines: toLines(commonRows),
  },
  {
    label: t('backend_settings.settings.mcp_server.privacy_mode.preview.group_affected'),
    lines: toLines(get(modeRows)),
  },
]);

const footers = computed<Record<McpPrivacyMode, string>>(() => ({
  [PrivacyMode.BALANCED]: t('backend_settings.settings.mcp_server.privacy_mode.preview.footer.balanced'),
  [PrivacyMode.RAW]: t('backend_settings.settings.mcp_server.privacy_mode.preview.footer.raw'),
  [PrivacyMode.STRICT]: t('backend_settings.settings.mcp_server.privacy_mode.preview.footer.strict'),
}));
const modeLabels = computed<Record<McpPrivacyMode, string>>(() => ({
  [PrivacyMode.BALANCED]: t('backend_settings.settings.mcp_server.privacy_mode.balanced.title'),
  [PrivacyMode.RAW]: t('backend_settings.settings.mcp_server.privacy_mode.raw.title'),
  [PrivacyMode.STRICT]: t('backend_settings.settings.mcp_server.privacy_mode.strict.title'),
}));
const footer = computed<string>(() => get(footers)[mode]);
const modeLabel = computed<string>(() => get(modeLabels)[mode]);
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-default bg-rui-grey-50 dark:bg-rui-grey-900">
    <div class="flex items-center justify-between gap-4 border-b border-default px-4 py-3">
      <span class="text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
        {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.title') }}
      </span>
      <span class="text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
        {{ modeLabel }}
      </span>
    </div>
    <div class="overflow-x-auto">
      <!-- table-fixed, because auto layout sizes the columns from their content: the values differ
           per mode, so the columns slid sideways on every switch. -->
      <table class="w-full min-w-[42rem] table-fixed text-left font-mono text-xs">
        <colgroup>
          <col class="w-40" />
          <col />
          <col />
        </colgroup>
        <thead class="text-rui-text-secondary">
          <tr class="border-b border-default">
            <th
              scope="col"
              class="px-4 py-2 font-medium"
            >
              {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.field') }}
            </th>
            <th
              scope="col"
              class="px-4 py-2 font-medium"
            >
              {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.swap') }}
            </th>
            <th
              scope="col"
              class="px-4 py-2 font-medium"
            >
              {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.deposit') }}
            </th>
          </tr>
        </thead>
        <tbody
          v-for="group in groups"
          :key="group.label"
        >
          <tr>
            <td
              colspan="3"
              class="border-b border-default px-4 pb-1 pt-3 font-sans text-[0.65rem] font-medium uppercase tracking-wider text-rui-text-secondary"
            >
              {{ group.label }}
            </td>
          </tr>
          <tr
            v-for="line in group.lines"
            :key="line.field"
            class="h-9 border-b border-default last:border-b-0"
          >
            <!-- Fixed row height and a reserved footer below: a chip is taller than a bare value,
                 so without them the card resizes on every mode switch and the page jumps. -->
            <th
              scope="row"
              class="whitespace-nowrap px-4 align-middle font-medium text-rui-text-secondary"
            >
              {{ line.field }}
            </th>
            <td
              v-for="(value, index) in line.cells"
              :key="index"
              class="whitespace-nowrap px-4 align-middle"
            >
              <span
                v-if="!value"
                class="italic text-rui-text-secondary"
              >
                {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.not_set') }}
              </span>
              <span
                v-else-if="value.kind === 'absent'"
                class="italic text-rui-text-disabled"
              >
                {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.not_sent') }}
              </span>
              <!-- No wrapping anywhere in here: a cell that breaks onto a second line would undo
                   the fixed row height and bring back the jump on mode switch. -->
              <span
                v-else-if="value.kind === 'hash'"
                class="rounded bg-rui-grey-200 px-1.5 py-0.5 text-rui-text-secondary dark:bg-rui-grey-800"
              >
                {{ value.text }}
              </span>
              <span
                v-else
                class="inline-flex items-center gap-x-2"
              >
                <span
                  v-if="value.kind === 'redacted'"
                  class="rounded bg-rui-grey-300 px-1.5 py-0.5 text-rui-text-secondary dark:bg-rui-grey-700"
                >
                  {{ value.text }}
                </span>
                <span v-else>{{ value.text }}</span>
                <span
                  v-if="value.flag"
                  class="text-rui-success"
                >
                  {{ value.flag }}
                </span>
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="min-h-16 border-t border-default px-4 py-3 font-sans text-sm text-rui-text-secondary">
      {{ footer }}
    </p>
  </div>
</template>
