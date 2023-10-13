<script setup lang="ts">
import {
  PrioritizedListData,
  type PrioritizedListItemData
} from '@/types/settings/prioritized-list-data';
import {
  COINGECKO_PRIO_LIST_ITEM,
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  MANUALCURRENT_PRIO_LIST_ITEM,
  MANUAL_PRIO_LIST_ITEM,
  type PrioritizedListId,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM
} from '@/types/settings/prioritized-list-id';

const currentOracles = ref<PrioritizedListId[]>([]);
const historicOracles = ref<PrioritizedListId[]>([]);

const { currentPriceOracles, historicalPriceOracles } = storeToRefs(
  useGeneralSettingsStore()
);

const resetCurrentPriceOracles = () => {
  set(currentOracles, get(currentPriceOracles));
};

const baseAvailableOraclesTyped: Array<
  PrioritizedListItemData<PrioritizedListId>
> = [
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM
];

const availableCurrentOracles = (): PrioritizedListData<PrioritizedListId> => {
  const itemData: Array<PrioritizedListItemData<PrioritizedListId>> = [
    ...baseAvailableOraclesTyped,
    UNISWAP2_PRIO_LIST_ITEM,
    UNISWAP3_PRIO_LIST_ITEM,
    MANUALCURRENT_PRIO_LIST_ITEM
  ];

  return new PrioritizedListData(itemData);
};

const availableHistoricOracles = (): PrioritizedListData<PrioritizedListId> => {
  const itemData: Array<PrioritizedListItemData<PrioritizedListId>> = [
    ...baseAvailableOraclesTyped,
    MANUAL_PRIO_LIST_ITEM
  ];

  return new PrioritizedListData(itemData);
};

const resetHistoricalPriceOracles = () => {
  set(historicOracles, get(historicalPriceOracles));
};

onMounted(() => {
  resetCurrentPriceOracles();
  resetHistoricalPriceOracles();
});

const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('price_oracle_settings.title') }}
    </template>
    <template #subtitle>
      {{ t('price_oracle_settings.subtitle') }}
    </template>

    <VRow>
      <VCol cols="12" md="6">
        <SettingsOption
          #default="{ error, success, update }"
          setting="currentPriceOracles"
          @finished="resetCurrentPriceOracles()"
        >
          <PrioritizedList
            :value="currentOracles"
            :all-items="availableCurrentOracles()"
            :status="{ error, success }"
            :item-data-name="t('price_oracle_settings.data_name').toString()"
            @input="update($event)"
          >
            <template #title>
              {{ t('price_oracle_settings.latest_prices') }}
            </template>
          </PrioritizedList>
        </SettingsOption>
      </VCol>

      <VCol cols="12" md="6">
        <SettingsOption
          #default="{ error, success, update }"
          setting="historicalPriceOracles"
          @finished="resetHistoricalPriceOracles()"
        >
          <PrioritizedList
            :value="historicOracles"
            :all-items="availableHistoricOracles()"
            :status="{ error, success }"
            :item-data-name="'price oracle'"
            @input="update($event)"
          >
            <template #title>
              {{ t('price_oracle_settings.historic_prices') }}
            </template>
          </PrioritizedList>
        </SettingsOption>
      </VCol>
    </VRow>
    <VRow>
      <VCol class="text-caption">
        {{ t('price_oracle_selection.hint') }}
      </VCol>
    </VRow>
  </SettingCategory>
</template>
