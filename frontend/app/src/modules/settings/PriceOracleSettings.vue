<script setup lang="ts">
import PriceRefresh from '@/modules/assets/prices/PriceRefresh.vue';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { PrioritizedListData, type PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import {
  ALCHEMY_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  KRAKEN_PRIO_LIST_ITEM,
  MORALIS_PRIO_LIST_ITEM,
  type PrioritizedListId,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
} from '@/modules/settings/types/prioritized-list-id';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

const { error: currentWriteError, model: currentOracles, success: currentWriteSuccess } = useSettingModel('currentPriceOracles', { debounce: 0 });
const { error: historicWriteError, model: historicOracles, success: historicWriteSuccess } = useSettingModel('historicalPriceOracles', { debounce: 0 });

const { clearAll: clearCurrent, error: currentError, setError: setCurrentError, setSuccess: setCurrentSuccess, success: currentSuccess } = useClearableMessages();
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

const historicalAvailableOraclesTyped: Array<PrioritizedListItemData<PrioritizedListId>> = [
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  ALCHEMY_PRIO_LIST_ITEM,
  MORALIS_PRIO_LIST_ITEM,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
];

const currentAvailableOraclesTyped: Array<PrioritizedListItemData<PrioritizedListId>> = [
  ...historicalAvailableOraclesTyped,
  KRAKEN_PRIO_LIST_ITEM,
];

function availableCurrentOracles(): PrioritizedListData<PrioritizedListId> {
  return new PrioritizedListData([...currentAvailableOraclesTyped]);
}

function availableHistoricalOracles(): PrioritizedListData<PrioritizedListId> {
  return new PrioritizedListData([...historicalAvailableOraclesTyped]);
}

const { reset: resetCachedHistoricalPrices } = useHistoricPriceCache();

const { t } = useI18n({ useScope: 'global' });

watch(currentOracles, () => {
  clearCurrent();
});

watch(currentWriteSuccess, (saved) => {
  if (saved)
    setCurrentSuccess(t('price_oracle_settings.latest_prices_update'), true);
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
    setHistoricSuccess('', true);
    resetCachedHistoricalPrices();
  }
});

watch(historicWriteError, (message) => {
  if (message)
    setHistoricError(message, true);
});
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="pb-5 flex flex-wrap gap-4 items-center justify-between border-b border-default">
      <SettingCategoryHeader>
        <template #title>
          {{ t('price_oracle_settings.title') }}
        </template>
        <template #subtitle>
          {{ t('price_oracle_settings.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <PriceRefresh
        @click="resetCachedHistoricalPrices()"
      />
    </div>
    <RuiAlert
      v-if="currentOracles.length === 0 || historicOracles.length === 0"
      type="warning"
    >
      {{ t('price_oracle_selection.hint') }}
    </RuiAlert>
    <div class="grid gap-4 lg:grid-cols-2">
      <PrioritizedList
        :model-value="currentOracles"
        :all-items="availableCurrentOracles()"
        :status="{ error: currentError, success: currentSuccess }"
        :item-data-name="t('price_oracle_settings.data_name')"
        @update:model-value="updateCurrentOracles($event)"
      >
        <template #title>
          {{ t('price_oracle_settings.latest_prices') }}
        </template>
      </PrioritizedList>

      <PrioritizedList
        :model-value="historicOracles"
        :all-items="availableHistoricalOracles()"
        :status="{ error: historicError, success: historicSuccess }"
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
