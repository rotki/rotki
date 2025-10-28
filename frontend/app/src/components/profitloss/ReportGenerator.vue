<script setup lang="ts">
import type { ProfitLossReportPeriod } from '@/types/reports';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useTransactionStatusCheck } from '@/modules/dashboard/progress/composables/use-transaction-status-check';
import { Routes } from '@/router/routes';
import { useSessionSettingsStore } from '@/store/settings/session';

const emit = defineEmits<{
  (e: 'generate', data: ProfitLossReportPeriod): void;
  (e: 'export-data', data: ProfitLossReportPeriod): void;
  (e: 'import-data'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const { isOutOfSync, navigateToHistory, processing } = useTransactionStatusCheck();
const { queryBinanceUserMarkets } = useExchangeApi();
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

const range = ref<ProfitLossReportPeriod>({ end: 0, start: 0 });
const valid = ref<boolean>(false);
const binanceExchangesWithoutMarkets = ref<string[]>([]);

const hasBinanceWithoutMarkets = computed<boolean>(() => get(binanceExchangesWithoutMarkets).length > 0);

const canGenerate = computed<boolean>(() => get(valid) && !get(processing) && !get(isOutOfSync) && !get(hasBinanceWithoutMarkets));

async function checkBinanceMarketPairs(): Promise<void> {
  const exchanges = get(connectedExchanges);
  const binanceExchanges = exchanges.filter(
    exchange => exchange.location === 'binance' || exchange.location === 'binanceus',
  );

  const exchangesWithoutMarkets: string[] = [];

  for (const exchange of binanceExchanges) {
    try {
      const markets = await queryBinanceUserMarkets(exchange.name, exchange.location);
      if (!markets || markets.length === 0)
        exchangesWithoutMarkets.push(exchange.name);
    }
    catch {
      // If we can't fetch markets, assume they're not set
      exchangesWithoutMarkets.push(exchange.name);
    }
  }

  set(binanceExchangesWithoutMarkets, exchangesWithoutMarkets);
}

function generate(): void {
  emit('generate', get(range));
}

function exportReportData(): void {
  emit('export-data', get(range));
}

function importReportData(): void {
  emit('import-data');
}

const accountSettingsRoute = Routes.SETTINGS_ACCOUNTING;
const exchangeSettingsRoute = Routes.API_KEYS_EXCHANGES;

onMounted(async () => {
  await checkBinanceMarketPairs();
});
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between px-4 py-2">
        <CardTitle>
          {{ t('common.actions.generate') }}
        </CardTitle>
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RouterLink :to="accountSettingsRoute">
              <RuiButton
                variant="text"
                icon
                color="primary"
              >
                <RuiIcon name="lu-settings" />
              </RuiButton>
            </RouterLink>
          </template>
          <span>{{ t('profit_loss_report.settings_tooltip') }}</span>
        </RuiTooltip>
      </div>
    </template>
    <RangeSelector
      v-model="range"
      @update:valid="valid = $event"
    />
    <RuiAlert
      v-if="isOutOfSync || processing"
      type="warning"
      class="mt-6"
    >
      <template v-if="processing">
        {{ t('profit_loss_report.processing_alert') }}
      </template>
      <template v-else>
        <div class="flex flex-col items-start gap-2">
          <div>{{ t('profit_loss_report.out_of_sync_alert') }}</div>
          <RuiButton
            size="sm"
            color="primary"
            variant="outlined"
            @click="navigateToHistory()"
          >
            {{ t('profit_loss_report.go_to_history') }}
          </RuiButton>
        </div>
      </template>
    </RuiAlert>
    <RuiAlert
      v-if="hasBinanceWithoutMarkets"
      type="warning"
      class="mt-6"
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
      <div class="flex gap-4 w-full">
        <div class="grow">
          <RuiButton
            class="w-full"
            color="primary"
            size="lg"
            :disabled="!canGenerate"
            @click="generate()"
          >
            <template #prepend>
              <RuiIcon name="lu-scroll-text" />
            </template>
            {{ t('common.actions.generate') }}
          </RuiButton>
        </div>
        <div>
          <RuiMenu
            close-on-content-click
            :popper="{ placement: 'bottom-end' }"
          >
            <template #activator="{ attrs }">
              <RuiButton
                class="h-[2.625rem]"
                size="lg"
                v-bind="attrs"
              >
                <template #prepend>
                  <RuiIcon name="lu-bug" />
                </template>
                {{ t('profit_loss_reports.debug.title') }}
              </RuiButton>
            </template>
            <div class="py-2">
              <RuiButton
                variant="list"
                @click="exportReportData()"
              >
                <template #prepend>
                  <RuiIcon name="lu-file-down" />
                </template>
                {{ t('profit_loss_reports.debug.export_data') }}
              </RuiButton>
              <RuiButton
                variant="list"
                @click="importReportData()"
              >
                <template #prepend>
                  <RuiIcon name="lu-file-up" />
                </template>
                {{ t('profit_loss_reports.debug.import_data') }}
              </RuiButton>
            </div>
          </RuiMenu>
        </div>
      </div>
    </template>
  </RuiCard>
</template>
