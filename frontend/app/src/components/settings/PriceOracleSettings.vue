<script setup lang="ts">
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import {
  PrioritizedListData,
  type PrioritizedListItemData
} from '@/types/prioritized-list-data';
import {
  COINGECKO_PRIO_LIST_ITEM,
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  MANUALCURRENT_PRIO_LIST_ITEM,
  MANUAL_PRIO_LIST_ITEM,
  type PrioritizedListId,
  SADDLE_PRIO_LIST_ITEM,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM
} from '@/types/prioritized-list-id';

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
    SADDLE_PRIO_LIST_ITEM,
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
  <setting-category>
    <template #title>
      {{ t('price_oracle_settings.title') }}
    </template>
    <template #subtitle>
      {{ t('price_oracle_settings.subtitle') }}
    </template>

    <v-row>
      <v-col cols="12" md="6">
        <settings-option
          #default="{ error, success, update }"
          setting="currentPriceOracles"
          @finished="resetCurrentPriceOracles"
        >
          <prioritized-list
            :value="currentOracles"
            :all-items="availableCurrentOracles()"
            :status="{ error, success }"
            :item-data-name="t('price_oracle_settings.data_name').toString()"
            @input="update"
          >
            <template #title>
              {{ t('price_oracle_settings.latest_prices') }}
            </template>
          </prioritized-list>
        </settings-option>
      </v-col>

      <v-col cols="12" md="6">
        <settings-option
          #default="{ error, success, update }"
          setting="historicalPriceOracles"
          @finished="resetHistoricalPriceOracles"
        >
          <prioritized-list
            :value="historicOracles"
            :all-items="availableHistoricOracles()"
            :status="{ error, success }"
            :item-data-name="'price oracle'"
            @input="update"
          >
            <template #title>
              {{ t('price_oracle_settings.historic_prices') }}
            </template>
          </prioritized-list>
        </settings-option>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="text-caption">
        {{ t('price_oracle_selection.hint') }}
      </v-col>
    </v-row>
  </setting-category>
</template>
