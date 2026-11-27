<script setup lang="ts">
import type { SeriesRange } from '@/modules/balances/account-history/balance-series';
import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';

const { account, asset, range } = defineProps<{
  account: string;
  asset: string;
  /** The chart's range; the list shows the events inside it. */
  range?: SeriesRange;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * Pins the list to the chart's account, asset and range, so it lists exactly the events
 * that moved the balance drawn above it, and the bar does not offer those filters again.
 */
const restrictions = computed<HistoryEventsRestrictions>(() => ({
  asset,
  // The account axis is matched by address alone, so the chain is not read.
  externalAccounts: [{ address: account, chain: '' }],
  period: range && range.from > 0 ? { fromTimestamp: range.from, toTimestamp: range.to } : undefined,
}));
</script>

<template>
  <HistoryEventsView
    :section-title="t('account_history.events.title')"
    :restrictions="restrictions"
    data-testid="account-history-events"
  />
</template>
