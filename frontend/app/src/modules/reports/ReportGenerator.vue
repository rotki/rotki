<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { ProfitLossReportPeriod } from '@/modules/reports/report-types';
import { startPromise } from '@shared/utils';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { useSyncRollup } from '@/modules/history/events/tx/use-sync-rollup';
import { useTransactionStatusCheck } from '@/modules/history/sync-status/use-transaction-status-check';
import RangeSelector from '@/modules/reports/RangeSelector.vue';
import ReportDebugMenu from '@/modules/reports/ReportDebugMenu.vue';
import { useBinanceMarketCheck } from '@/modules/reports/use-binance-market-check';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const emit = defineEmits<{
  'generate': [data: ProfitLossReportPeriod];
  'export-data': [data: ProfitLossReportPeriod];
  'import-data': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isOutOfSync, processing } = useTransactionStatusCheck();
const { progress: overallProgress } = useSyncRollup();
const { refreshTransactions } = useHistoryTransactions();
const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

const {
  checkMarketPairs,
  exchangesWithoutMarkets: binanceExchangesWithoutMarkets,
  hasExchangesWithoutMarkets: hasBinanceWithoutMarkets,
} = useBinanceMarketCheck(connectedExchanges);

const range = ref<{ start: number | undefined; end: number }>({ end: 0, start: undefined });
const valid = ref<boolean>(false);

const canGenerate = computed<boolean>(() => get(valid) && !get(processing) && !get(isOutOfSync) && !get(hasBinanceWithoutMarkets));

function toReportPeriod(): ProfitLossReportPeriod {
  const { end, start } = get(range);
  return { end, start: start ?? 0 };
}

function generate(): void {
  emit('generate', toReportPeriod());
}

function syncHistory(): void {
  startPromise(refreshTransactions({ userInitiated: true }));
}

function exportReportData(): void {
  emit('export-data', toReportPeriod());
}

function importReportData(): void {
  emit('import-data');
}

const exchangeSettingsRoute: RouteLocationRaw = { name: '/api-keys/exchanges/' };

onMounted(async () => {
  await checkMarketPairs();
});
</script>

<template>
  <RuiCard :class-names="{ content: 'pt-0!' }">
    <template #header>
      <span class="text-base font-semibold">
        {{ t('profit_loss_report.generate_title') }}
      </span>
    </template>
    <RangeSelector
      v-model="range"
      @update:valid="valid = $event"
    />
    <RuiAlert
      v-if="isOutOfSync || processing"
      type="warning"
      class="mt-4"
    >
      <div class="flex flex-col items-start gap-2">
        <div>
          {{ processing ? t('profit_loss_report.processing_alert', { percentage: overallProgress }) : t('profit_loss_report.out_of_sync_alert') }}
        </div>
        <RuiButton
          size="sm"
          color="primary"
          variant="outlined"
          :loading="processing"
          :disabled="processing"
          data-testid="report-generator-sync-history"
          @click="syncHistory()"
        >
          {{ t('profit_loss_report.sync_history') }}
        </RuiButton>
      </div>
    </RuiAlert>
    <RuiAlert
      v-if="hasBinanceWithoutMarkets"
      type="warning"
      class="mt-4"
    >
      <div class="flex flex-col items-start gap-2">
        <div class="whitespace-break-spaces">
          {{ t('profit_loss_report.binance_markets_alert', { exchanges: binanceExchangesWithoutMarkets.map(item => `- ${item}`).join('\n') }) }}
        </div>
        <RouterLink :to="exchangeSettingsRoute">
          <RuiButton
            size="sm"
            color="primary"
            variant="outlined"
          >
            {{ t('profit_loss_report.go_to_exchanges') }}
          </RuiButton>
        </RouterLink>
      </div>
    </RuiAlert>
    <template #footer>
      <div class="flex items-center justify-between gap-2 w-full">
        <ReportDebugMenu
          @export-data="exportReportData()"
          @import-data="importReportData()"
        />
        <div class="flex items-center gap-4 min-w-0">
          <span
            v-if="range.start !== undefined && range.end > 0"
            class="text-sm text-rui-text-secondary truncate"
            data-testid="report-range-summary"
          >
            <template v-if="range.start === 0">
              {{ t('generate.summary_all_time') }}
            </template>
            <i18n-t
              v-else
              scope="global"
              keypath="profit_loss_report.report_period"
            >
              <template #start>
                <DateDisplay
                  no-time
                  :timestamp="range.start"
                />
              </template>
              <template #end>
                <DateDisplay
                  no-time
                  :timestamp="range.end"
                />
              </template>
            </i18n-t>
          </span>
          <RuiButton
            color="primary"
            class="shrink-0"
            :disabled="!canGenerate"
            data-testid="generate-report"
            @click="generate()"
          >
            <template #prepend>
              <RuiIcon name="lu-scroll-text" />
            </template>
            {{ t('common.actions.generate') }}
          </RuiButton>
        </div>
      </div>
    </template>
  </RuiCard>
</template>
