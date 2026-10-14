<script setup lang="ts">
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import PriceRefresh from '@/modules/assets/prices/PriceRefresh.vue';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { CURRENT_PRICE_ORACLE_ITEMS, HISTORICAL_PRICE_ORACLE_ITEMS } from '@/modules/settings/price-oracle-lists';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { PrioritizedListData } from '@/modules/settings/types/prioritized-list-data';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

const { error: currentWriteError, model: currentOracles, success: currentWriteSuccess } = useSettingModel('currentPriceOracles', { debounce: 0 });
const { error: historicWriteError, model: historicOracles, success: historicWriteSuccess } = useSettingModel('historicalPriceOracles', { debounce: 0 });

const { clearAll: clearCurrent, error: currentError, setError: setCurrentError, success: currentSuccess } = useClearableMessages();
const { clearAll: clearHistoric, error: historicError, setError: setHistoricError, setSuccess: setHistoricSuccess, success: historicSuccess } = useClearableMessages();

const priceOracleValues: string[] = Object.values(PriceOracle);

function isPriceOracle(value: PrioritizedListId): value is PriceOracle {
  return priceOracleValues.includes(value);
}

function updateCurrentOracles(value: PrioritizedListId[]): void {
  set(currentOracles, value.filter(isPriceOracle));
}

function updateHistoricOracles(value: PrioritizedListId[]): void {
  set(historicOracles, value.filter(isPriceOracle));
}

function availableCurrentOracles(): PrioritizedListData<PrioritizedListId> {
  return new PrioritizedListData([...CURRENT_PRICE_ORACLE_ITEMS]);
}

function availableHistoricalOracles(): PrioritizedListData<PrioritizedListId> {
  return new PrioritizedListData([...HISTORICAL_PRICE_ORACLE_ITEMS]);
}

const { reset: resetCachedHistoricalPrices } = useHistoricPriceCache();
const { refreshing, refreshPrices } = usePriceRefresh();

const { t } = useI18n({ useScope: 'global' });

/**
 * A saved latest order only applies to prices fetched after it, so the list keeps saying so, with a
 * way to refresh, until the prices are refreshed or the order changes again. Unlike a plain "saved",
 * it does not fade on a timer.
 */
const awaitingRefresh = ref<boolean>(false);

const currentStatus = computed<BaseMessage>(() => ({
  error: get(currentError),
  success: get(awaitingRefresh) ? t('price_oracle_settings.status.saved_refresh') : get(currentSuccess),
}));

const historicStatus = computed<BaseMessage>(() => ({
  error: get(historicError),
  success: get(historicSuccess),
}));

async function refreshNow(): Promise<void> {
  set(awaitingRefresh, false);
  resetCachedHistoricalPrices();
  await refreshPrices(true);
}

function onRefreshClick(): void {
  set(awaitingRefresh, false);
  resetCachedHistoricalPrices();
}

watch(currentOracles, () => {
  clearCurrent();
  set(awaitingRefresh, false);
});

watch(currentWriteSuccess, (saved) => {
  if (saved)
    set(awaitingRefresh, true);
});

watch(currentWriteError, (message) => {
  if (message)
    setCurrentError(message, true);
});

watch(historicOracles, () => {
  clearHistoric();
});

watch(historicWriteSuccess, (saved) => {
  if (saved) {
    setHistoricSuccess(t('price_oracle_settings.status.cache_cleared'));
    resetCachedHistoricalPrices();
  }
});

watch(historicWriteError, (message) => {
  if (message)
    setHistoricError(message, true);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="pb-4 flex items-start justify-between gap-4 border-b border-rui-divider">
      <SettingCategoryHeader class="flex-1">
        <template #title>
          {{ t('price_oracle_settings.title') }}
        </template>
        <template #subtitle>
          {{ t('price_oracle_settings.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <PriceRefresh
        @click="onRefreshClick()"
      />
    </div>
    <div class="grid gap-4 lg:grid-cols-2">
      <PrioritizedList
        :model-value="currentOracles"
        :all-items="availableCurrentOracles()"
        :status="currentStatus"
        :empty-warning="t('price_oracle_settings.empty_warning')"
        :item-data-name="t('price_oracle_settings.data_name')"
        @update:model-value="updateCurrentOracles($event)"
      >
        <template #title>
          {{ t('price_oracle_settings.latest_prices') }}
        </template>
        <template
          v-if="awaitingRefresh"
          #status
        >
          {{ t('price_oracle_settings.status.saved_refresh') }}
          <RuiButton
            variant="text"
            color="primary"
            size="sm"
            class="-my-1 px-1!"
            :disabled="refreshing"
            data-testid="oracle-refresh-now"
            @click="refreshNow()"
          >
            {{ t('price_oracle_settings.status.refresh_now') }}
          </RuiButton>
        </template>
      </PrioritizedList>

      <PrioritizedList
        :model-value="historicOracles"
        :all-items="availableHistoricalOracles()"
        :status="historicStatus"
        :empty-warning="t('price_oracle_settings.empty_warning')"
        :item-data-name="t('price_oracle_settings.data_name')"
        @update:model-value="updateHistoricOracles($event)"
      >
        <template #title>
          {{ t('price_oracle_settings.historic_prices') }}
        </template>
      </PrioritizedList>
    </div>
  </div>
</template>
