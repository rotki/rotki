<script setup lang="ts">
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { PrioritizedListData, type PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import {
  ALCHEMY_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  MANUAL_PRIO_LIST_ITEM,
  type PrioritizedListId,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
  YAHOOFINANCE_PRIO_LIST_ITEM,
} from '@/types/settings/prioritized-list-id';

const currentOracles = ref<PrioritizedListId[]>([]);
const historicOracles = ref<PrioritizedListId[]>([]);

const { currentPriceOracles, historicalPriceOracles } = storeToRefs(useGeneralSettingsStore());

function resetCurrentPriceOracles() {
  set(currentOracles, get(currentPriceOracles));
}

const baseAvailableOraclesTyped: Array<PrioritizedListItemData<PrioritizedListId>> = [
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  ALCHEMY_PRIO_LIST_ITEM,
  YAHOOFINANCE_PRIO_LIST_ITEM,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
];

function availableCurrentOracles(): PrioritizedListData<PrioritizedListId> {
  return new PrioritizedListData([...baseAvailableOraclesTyped]);
}

function availableHistoricOracles(): PrioritizedListData<PrioritizedListId> {
  const itemData: Array<PrioritizedListItemData<PrioritizedListId>> = [
    ...baseAvailableOraclesTyped,
    MANUAL_PRIO_LIST_ITEM,
  ];

  return new PrioritizedListData(itemData);
}

const { reset: resetCachedHistoricalPrices } = useHistoricCachePriceStore();

function resetHistoricalPriceOracles(resetPrices: boolean = false) {
  set(historicOracles, get(historicalPriceOracles));

  if (resetPrices)
    resetCachedHistoricalPrices();
}

onMounted(() => {
  resetCurrentPriceOracles();
  resetHistoricalPriceOracles();
});

const { t } = useI18n();
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
    <div class="grid grid-flow-col gap-4 grid-rows-[repeat(4,auto)] lg:grid-rows-[repeat(2,auto)] lg:grid-cols-2">
      <SettingsOption
        #default="{ error, success, updateImmediate }"
        setting="currentPriceOracles"
        :success-message="t('price_oracle_settings.latest_prices_update')"
        @finished="resetCurrentPriceOracles()"
      >
        <PrioritizedList
          :model-value="currentOracles"
          :all-items="availableCurrentOracles()"
          :status="{ error, success }"
          :item-data-name="t('price_oracle_settings.data_name')"
          @update:model-value="updateImmediate($event)"
        >
          <template #title>
            {{ t('price_oracle_settings.latest_prices') }}
          </template>
        </PrioritizedList>
      </SettingsOption>

      <SettingsOption
        #default="{ error, success, updateImmediate }"
        setting="historicalPriceOracles"
        @finished="resetHistoricalPriceOracles(true)"
      >
        <PrioritizedList
          :model-value="historicOracles"
          :all-items="availableHistoricOracles()"
          :status="{ error, success }"
          :item-data-name="t('price_oracle_settings.data_name')"
          @update:model-value="updateImmediate($event)"
        >
          <template #title>
            {{ t('price_oracle_settings.historic_prices') }}
          </template>
        </PrioritizedList>
      </SettingsOption>
    </div>
  </div>
</template>
