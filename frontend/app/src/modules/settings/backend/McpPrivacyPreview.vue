<script setup lang="ts">
import { type McpPrivacyMode, McpPrivacyMode as PrivacyMode } from '@/modules/settings/types/mcp';

const { mode } = defineProps<{
  mode: McpPrivacyMode;
}>();

const { t } = useI18n({ useScope: 'global' });

interface PreviewRow {
  readonly field: string;
  readonly deposit?: string;
  readonly swap?: string;
}

const commonRows: PreviewRow[] = [
  { deposit: '1754425840000', field: 'timestamp', swap: '1754431200000' },
  { deposit: 'kraken', field: 'location', swap: 'ethereum' },
  { deposit: 'deposit', field: 'event_type', swap: 'trade' },
  { deposit: 'BTC', field: 'asset', swap: 'ETH' },
  { deposit: '0.4', field: 'amount', swap: '1.25' },
  { field: 'counterparty', swap: 'uniswap-v3' },
];

const modeRows = computed<PreviewRow[]>(() => {
  if (mode === PrivacyMode.RAW) {
    return [
      { deposit: 'Kraken main', field: 'location_label', swap: '0x9C5083…5dAC5' },
      { field: 'tx_hash', swap: '0x3f1a…9d2c' },
      { deposit: 'Deposit 0.4 BTC to Kraken', field: 'auto_notes', swap: 'Swap 1.25 ETH for 4381.25 USDC' },
      { field: 'user_notes', swap: 'quarterly rebalance' },
    ];
  }

  if (mode === PrivacyMode.BALANCED) {
    return [
      { deposit: 'Kraken main', field: 'location_label', swap: 'anon_5c4efe77c7146ef8' },
      { field: 'tx_hash', swap: 'anon_61b73c8e638bc34c' },
      { deposit: 'Deposit 0.4 BTC to Kraken', field: 'auto_notes', swap: 'Swap 1.25 ETH for 4381.25 USDC' },
      { field: 'user_notes', swap: '[redacted] · has_user_notes: true' },
    ];
  }

  return [
    { deposit: 'anon_b43a5d4cd838add9', field: 'location_label', swap: 'anon_5c4efe77c7146ef8' },
    { field: 'tx_hash', swap: 'anon_61b73c8e638bc34c' },
    { deposit: '[redacted] · has_auto_notes: true', field: 'auto_notes', swap: '[redacted] · has_auto_notes: true' },
    { field: 'user_notes', swap: '[redacted] · has_user_notes: true' },
  ];
});

const rows = computed<PreviewRow[]>(() => [...commonRows, ...get(modeRows)]);
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
    <div class="flex items-center justify-between border-b border-default px-4 py-3">
      <span class="text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
        {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.title') }}
      </span>
      <span class="text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
        {{ modeLabel }}
      </span>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full min-w-[42rem] text-left font-mono text-xs">
        <thead class="text-rui-text-secondary">
          <tr class="border-b border-default">
            <th class="px-4 py-2 font-medium">
              {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.field') }}
            </th>
            <th class="px-4 py-2 font-medium">
              {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.swap') }}
            </th>
            <th class="px-4 py-2 font-medium">
              {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.deposit') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.field"
            class="border-b border-default last:border-b-0"
          >
            <th class="px-4 py-2 font-medium text-rui-text-secondary">
              {{ row.field }}
            </th>
            <td class="px-4 py-2">
              <span v-if="row.swap">{{ row.swap }}</span>
              <span
                v-else
                class="italic text-rui-text-secondary"
              >
                {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.not_set') }}
              </span>
            </td>
            <td class="px-4 py-2">
              <span v-if="row.deposit">{{ row.deposit }}</span>
              <span
                v-else
                class="italic text-rui-text-secondary"
              >
                {{ t('backend_settings.settings.mcp_server.privacy_mode.preview.not_set') }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="border-t border-default px-4 py-3 text-sm text-rui-text-secondary">
      {{ footer }}
    </p>
  </div>
</template>
