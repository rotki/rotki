<script setup lang="ts">
import type { HistoricalPrice, HistoricalPriceDeletePayload, HistoricalPriceFormPayload } from '@/types/prices';
import type { EditableMissingPrice } from '@/types/reports';
import type { BigNumber, FailedHistoricalAssetPriceResponse } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { ApiValidationError } from '@/types/api/errors';

const props = defineProps<{
  asset: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const prices = ref<HistoricalPrice[]>([]);
const errorMessages = ref<Record<string, string[]>>({});

const refreshedHistoricalPrices = ref<Record<string, BigNumber>>({});
const sort = ref<DataTableSortData<EditableMissingPrice>>([]);
const tab = ref(0);

const { assetName } = useAssetInfoRetrieval();
const store = useHistoricCachePriceStore();
const { failedDailyPrices, resolvedFailedDailyPrices } = storeToRefs(store);
const { resetHistoricalPricesData } = store;
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();

const name = assetName(props.asset);

const failedPrices = computed<FailedHistoricalAssetPriceResponse>(() => get(failedDailyPrices)[props.asset]);

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

const formattedItems = computed<EditableMissingPrice[]>(() => {
  const fromAsset = props.asset;
  const toAsset = get(currencySymbol);

  return get(failedPrices).noPricesTimestamps.map((time) => {
    const savedHistoricalPrice = get(prices).find(
      price => price.fromAsset === fromAsset && price.toAsset === toAsset && price.timestamp === time,
    );

    const savedPrice = savedHistoricalPrice?.price;
    const refreshedHistoricalPrice = get(refreshedHistoricalPrices)[time];

    const useRefreshedHistoricalPrice = !savedPrice && !!refreshedHistoricalPrice;

    const price = (useRefreshedHistoricalPrice ? refreshedHistoricalPrice : savedPrice)?.toFixed() ?? '';

    return {
      fromAsset,
      price,
      saved: !!savedPrice,
      time,
      toAsset,
      useRefreshedHistoricalPrice,
    };
  });
});

async function getHistoricalPrices() {
  set(prices, await fetchHistoricalPrices());
}

async function updatePrice(item: EditableMissingPrice) {
  if (item.useRefreshedHistoricalPrice)
    return;

  const payload: HistoricalPriceDeletePayload = {
    fromAsset: item.fromAsset,
    timestamp: item.time,
    toAsset: item.toAsset,
  };

  try {
    if (item.price) {
      const formPayload: HistoricalPriceFormPayload = {
        ...payload,
        price: item.price,
      };

      if (item.saved)
        await editHistoricalPrice(formPayload);
      else await addHistoricalPrice(formPayload);
    }
    else if (item.saved) {
      await deleteHistoricalPrice(payload);
    }
  }
  catch (error: any) {
    let errorMessage = error.message;
    if (error instanceof ApiValidationError) {
      const errors = error.getValidationErrors({ price: '' });
      errorMessage = typeof errors === 'string' ? error.message : errors.price[0];
    }

    set(errorMessages, {
      ...get(errorMessages),
      [item.time]: errorMessage,
    });
  }

  resetHistoricalPricesData([payload]);
  const resolved = { ...get(resolvedFailedDailyPrices) };
  const assetResolved = resolved[item.fromAsset];
  if (assetResolved) {
    assetResolved.push(item.time);
  }
  else {
    resolved[item.fromAsset] = [item.time];
  }
  set(resolvedFailedDailyPrices, resolved);

  await getHistoricalPrices();
}

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
                @focus="delete errorMessages[row.time]"
                @update:model-value="delete errorMessages[row.time]"
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
        @click="emit('close')"
      >
        {{ t('common.actions.close') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
