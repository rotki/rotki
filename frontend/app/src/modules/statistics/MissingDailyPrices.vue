<script setup lang="ts">
import type { FailedHistoricalAssetPriceResponse } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { EditableMissingPrice, MissingPrice } from '@/modules/reports/report-types';
import { get, set } from '@vueuse/shared';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEditableMissingPrices } from '@/modules/assets/prices/use-editable-missing-prices';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { useSetting } from '@/modules/settings/use-setting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import { dayStart } from '@/modules/statistics/pricing/backfill-plan';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

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
const priceSeries = usePriceSeriesStore();
const currencySymbol = useSetting('currencySymbol');

const name = useAssetField(() => asset, 'name');

const failedPrices = computed<FailedHistoricalAssetPriceResponse>(() => get(failedDailyPrices)[asset]);

/**
 * The first of the times filed for each UTC day, oldest first. The daily price fetcher and the
 * backfill file the same day at different times and in no particular order, and the dialog shows
 * each day once, in date order.
 */
function oncePerDay(times: readonly number[]): number[] {
  const byDay = new Map<number, number>();
  for (const time of times) {
    if (!byDay.has(dayStart(time)))
      byDay.set(dayStart(time), time);
  }
  return [...byDay.values()].sort((a, b) => a - b);
}

const rateLimitedDays = computed<number[]>(() => oncePerDay(get(failedPrices).rateLimitedPricesTimestamps));
const unreachableDays = computed<number[]>(() => oncePerDay(get(failedPrices).failedPricesTimestamps));

/**
 * The days a price can be entered for by hand: the ones with no price, and the ones the price
 * sources could not be reached for, since a source that stays unreachable would never fill them.
 */
const missingPrices = computed<MissingPrice[]>(() => {
  const { failedPricesTimestamps, noPricesTimestamps } = get(failedPrices);
  return oncePerDay([...noPricesTimestamps, ...failedPricesTimestamps]).map(time => ({
    fromAsset: asset,
    time,
    toAsset: get(currencySymbol),
  }));
});

/** A price entered for a day settles every time filed for that day. */
function markResolved(item: EditableMissingPrice): void {
  const { failedPricesTimestamps, noPricesTimestamps } = get(failedPrices);
  const day = dayStart(item.time);
  const times = [item.time, ...noPricesTimestamps, ...failedPricesTimestamps].filter(time => dayStart(time) === day);
  const resolved = get(resolvedFailedDailyPrices);
  set(resolvedFailedDailyPrices, {
    ...resolved,
    [item.fromAsset]: [...new Set([...(resolved[item.fromAsset] ?? []), ...times])],
  });
}

/**
 * A deleted price unsettles its day again: the graphs drop the price they took from it and read
 * the cache again, since another price may still be cached for that day. The cache answers with a
 * price up to a day away, so the points of the days on either side may hold it too.
 */
function markUnresolved(item: EditableMissingPrice): void {
  const day = dayStart(item.time);
  const resolved = get(resolvedFailedDailyPrices);
  priceSeries.removeDays(item.fromAsset, new Set([day - SECONDS_PER_DAY, day, day + SECONDS_PER_DAY]));
  set(resolvedFailedDailyPrices, {
    ...resolved,
    [item.fromAsset]: (resolved[item.fromAsset] ?? []).filter(time => dayStart(time) !== day),
  });
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
  onPriceDeleted: markUnresolved,
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
      <RuiTab v-if="missingPrices.length > 0">
        {{ t('premium_components.statistics.failed_daily_prices.missing_prices.title') }}
      </RuiTab>
      <RuiTab v-if="rateLimitedDays.length > 0">
        {{ t('premium_components.statistics.failed_daily_prices.rate_limited.title') }}
      </RuiTab>
      <RuiTab v-if="unreachableDays.length > 0">
        {{ t('premium_components.statistics.failed_daily_prices.unreachable.title') }}
      </RuiTab>
    </RuiTabs>
    <div class="max-h-[calc(100vh-18rem)]! overflow-auto px-4 pt-3 pb-4">
      <RuiTabItems
        v-model="tab"
        class="overflow-y-auto"
      >
        <RuiTabItem
          v-if="missingPrices.length > 0"
        >
          <div class="text-rui-text-secondary whitespace-pre">
            {{
              t(
                'premium_components.statistics.failed_daily_prices.missing_prices.description', {
                  length: missingPrices.length,
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
          v-if="rateLimitedDays.length > 0"
        >
          <div class="text-rui-text-secondary">
            {{
              t('premium_components.statistics.failed_daily_prices.rate_limited.description', {
                length: rateLimitedDays.length,
              })
            }}
          </div>
          <ul class="list-disc mt-4">
            <li
              v-for="timestamp in rateLimitedDays"
              :key="timestamp"
            >
              <DateDisplay :timestamp="timestamp" />
            </li>
          </ul>
        </RuiTabItem>
        <RuiTabItem
          v-if="unreachableDays.length > 0"
        >
          <div class="text-rui-text-secondary">
            {{
              t('premium_components.statistics.failed_daily_prices.unreachable.description', {
                length: unreachableDays.length,
              })
            }}
          </div>
          <ul class="list-disc mt-4">
            <li
              v-for="timestamp in unreachableDays"
              :key="timestamp"
              data-testid="missing-daily-prices-unreachable"
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
