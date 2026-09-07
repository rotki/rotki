<script setup lang="ts">
import type { FailedHistoricalAssetPriceResponse } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { EditableMissingPrice, MissingPrice } from '@/modules/reports/report-types';
import { useEditableMissingPrices } from '@/modules/assets/prices/use-editable-missing-prices';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useSetting } from '@/modules/settings/use-setting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const { asset } = defineProps<{
  asset: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<EditableMissingPrice>>([]);
const tab = ref<number>(0);

const { useAssetField } = useAssetInfoRetrieval();
const { failedDailyPrices, resolvedFailedDailyPrices } = useHistoricPriceCache();
const currencySymbol = useSetting('currencySymbol');

const name = useAssetField(() => asset, 'name');

const failedPrices = computed<FailedHistoricalAssetPriceResponse>(() => get(failedDailyPrices)[asset]);

const missingPrices = computed<MissingPrice[]>(() => get(failedPrices).noPricesTimestamps.map(time => ({
  fromAsset: asset,
  time,
  toAsset: get(currencySymbol),
})));

function markResolved(item: EditableMissingPrice): void {
  const resolved = { ...get(resolvedFailedDailyPrices) };
  const assetResolved = resolved[item.fromAsset];
  if (assetResolved) {
    assetResolved.push(item.time);
  }
  else {
    resolved[item.fromAsset] = [item.time];
  }
  set(resolvedFailedDailyPrices, resolved);
}

const {
  clearError,
  errorMessages,
  formattedItems,
  getHistoricalPrices,
  updatePrice,
} = useEditableMissingPrices({
  items: missingPrices,
  keyOf: item => item.time.toString(),
  onPriceUpdated: markResolved,
});

const headers = computed<DataTableColumn<EditableMissingPrice>[]>(() => [
  {
    key: 'time',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    key: 'price',
    label: t('common.price'),
  },
]);

onMounted(async () => {
  await getHistoricalPrices();
});
</script>

<template>
  <RuiCard
    divide
    no-padding
  >
    <template #header>
      {{ t('premium_components.statistics.failed_daily_prices.dialog_title', { name }) }}
    </template>
    <RuiTabs
      v-model="tab"
      color="primary"
      class="px-4 mt-2"
    >
      <RuiTab v-if="failedPrices.noPricesTimestamps.length > 0">
        {{ t('premium_components.statistics.failed_daily_prices.missing_prices.title') }}
      </RuiTab>
      <RuiTab v-if="failedPrices.rateLimitedPricesTimestamps.length > 0">
        {{ t('premium_components.statistics.failed_daily_prices.rate_limited.title') }}
      </RuiTab>
    </RuiTabs>
    <div class="!max-h-[calc(100vh-18rem)] overflow-auto px-4 pt-3 pb-4">
      <RuiTabItems
        v-model="tab"
        class="overflow-y-auto"
      >
        <RuiTabItem
          v-if="failedPrices.noPricesTimestamps.length > 0"
        >
          <div class="text-rui-text-secondary whitespace-pre">
            {{
              t(
                'premium_components.statistics.failed_daily_prices.missing_prices.description', {
                  length: failedPrices.noPricesTimestamps.length,
                })
            }}
          </div>
          <RuiDataTable
            v-model:sort="sort"
            outlined
            class="mt-2"
            :cols="headers"
            :rows="formattedItems"
            row-attr="fromAsset"
          >
            <template #item.time="{ row }">
              <DateDisplay :timestamp="row.time" />
            </template>
            <template #item.price="{ row }">
              <AmountInput
                v-model="row.price"
                dense
                :disabled="row.useRefreshedHistoricalPrice"
                :label="t('profit_loss_report.actionable.missing_prices.input_price')"
                variant="outlined"
                :success-messages="row.saved ? [t('profit_loss_report.actionable.missing_prices.price_is_saved')] : []"
                :error-messages="errorMessages[row.time]"
                data-testid="missing-daily-price-input"
                @focus="clearError(row)"
                @update:model-value="clearError(row)"
                @blur="updatePrice(row)"
              />
            </template>
          </RuiDataTable>
        </RuiTabItem>
        <RuiTabItem
          v-if="failedPrices.rateLimitedPricesTimestamps.length > 0"
        >
          <div class="text-rui-text-secondary">
            {{
              t('premium_components.statistics.failed_daily_prices.rate_limited.description', {
                length: failedPrices.rateLimitedPricesTimestamps.length,
              })
            }}
          </div>
          <ul class="list-disc mt-4">
            <li
              v-for="timestamp in failedPrices.rateLimitedPricesTimestamps"
              :key="timestamp"
            >
              <DateDisplay :timestamp="timestamp" />
            </li>
          </ul>
        </RuiTabItem>
      </RuiTabItems>
    </div>
    <template #footer>
      <div class="grow" />
      <RuiButton
        color="primary"
        class="mt-2"
        data-testid="close-missing-daily-prices"
        @click="emit('close')"
      >
        {{ t('common.actions.close') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
