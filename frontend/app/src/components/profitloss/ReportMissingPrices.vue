<script setup lang="ts">
import type { HistoricalPrice, HistoricalPriceDeletePayload, HistoricalPriceFormPayload } from '@/types/prices';
import type { EditableMissingPrice, MissingPrice } from '@/types/reports';
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useBalancePricesStore } from '@/store/balances/prices';
import { ApiValidationError } from '@/types/api/errors';

const props = defineProps<{
  items: MissingPrice[];
  isPinned: boolean;
}>();

defineSlots<{
  actions: (props: { items: EditableMissingPrice[] }) => any;
}>();

const { t } = useI18n();
const { isPinned, items } = toRefs(props);
const prices = ref<HistoricalPrice[]>([]);
const errorMessages = ref<Record<string, string[]>>({});
const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();

function createKey(item: MissingPrice) {
  return item.fromAsset + item.toAsset + item.time;
}

async function getHistoricalPrices() {
  set(prices, await fetchHistoricalPrices());
}

onMounted(async () => {
  await getHistoricalPrices();
});

const refreshedHistoricalPrices = ref<Record<string, BigNumber>>({});
const sort = ref<DataTableSortData<EditableMissingPrice>>([]);

const formattedItems = computed<EditableMissingPrice[]>(() =>
  get(items).map((item) => {
    const savedHistoricalPrice = get(prices).find(
      price => price.fromAsset === item.fromAsset && price.toAsset === item.toAsset && price.timestamp === item.time,
    );

    const key = createKey(item);
    const savedPrice = savedHistoricalPrice?.price;
    const refreshedHistoricalPrice = get(refreshedHistoricalPrices)[key];

    const useRefreshedHistoricalPrice = !savedPrice && !!refreshedHistoricalPrice;

    const price = (useRefreshedHistoricalPrice ? refreshedHistoricalPrice : savedPrice)?.toFixed() ?? '';

    return {
      ...item,
      price,
      saved: !!savedPrice,
      useRefreshedHistoricalPrice,
    };
  }),
);

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
      [createKey(item)]: errorMessage,
    });
  }

  await getHistoricalPrices();
}

const tableRef = ref();

const tableContainer = computed(() => get(tableRef)?.$el);

const headers = computed<DataTableColumn<EditableMissingPrice>[]>(() => [
  {
    key: 'fromAsset',
    label: t('profit_loss_report.actionable.missing_prices.headers.from_asset'),
    sortable: true,
  },
  {
    cellClass: get(isPinned) ? 'px-2' : '',
    key: 'toAsset',
    label: t('profit_loss_report.actionable.missing_prices.headers.to_asset'),
    sortable: true,
  },
  {
    cellClass: get(isPinned) ? 'px-2' : '',
    key: 'time',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: `pb-1 ${get(isPinned) ? '' : ''}`,
    key: 'price',
    label: t('common.price'),
  },
]);

useRememberTableSorting<EditableMissingPrice>(TableId.REPORTS_MISSING_PRICES, sort, headers);

const { getHistoricPrice } = useBalancePricesStore();

const refreshing = ref<boolean>(false);

async function refreshHistoricalPrice(item: EditableMissingPrice) {
  set(refreshing, true);
  const rateFromHistoricPrice = await getHistoricPrice({
    fromAsset: item.fromAsset,
    timestamp: item.time,
    toAsset: item.toAsset,
  });

  const key = createKey(item);
  if (rateFromHistoricPrice && rateFromHistoricPrice.gt(0)) {
    const refreshedHistoricalPricesVal = get(refreshedHistoricalPrices);
    refreshedHistoricalPricesVal[key] = rateFromHistoricPrice;
    set(refreshedHistoricalPrices, refreshedHistoricalPricesVal);
  }
  else {
    set(errorMessages, {
      ...get(errorMessages),
      [key]: t('profit_loss_report.actionable.missing_prices.price_not_found'),
    });
  }
  set(refreshing, false);
}
</script>

<template>
  <div>
    <RuiDataTable
      ref="tableRef"
      v-model:sort="sort"
      class="table-inside-dialog"
      :class="{
        [$style['table--pinned']]: isPinned,
      }"
      :cols="headers"
      :rows="formattedItems"
      :scroller="tableContainer"
      :dense="isPinned"
      row-attr="fromAsset"
    >
      <template #item.fromAsset="{ row }">
        <AssetDetails
          link
          :asset="row.fromAsset"
        />
      </template>
      <template #item.toAsset="{ row }">
        <AssetDetails
          link
          :asset="row.toAsset"
        />
      </template>
      <template #item.time="{ row }">
        <DateDisplay :timestamp="row.time" />
      </template>
      <template #item.price="{ row }">
        <AmountInput
          v-model="row.price"
          :class="$style.input"
          dense
          :disabled="row.useRefreshedHistoricalPrice"
          :label="t('profit_loss_report.actionable.missing_prices.input_price')"
          variant="outlined"
          :success-messages="row.saved ? [t('profit_loss_report.actionable.missing_prices.price_is_saved')] : []"
          :error-messages="errorMessages[createKey(row)]"
          @focus="delete errorMessages[createKey(row)]"
          @update:model-value="delete errorMessages[createKey(row)]"
          @blur="updatePrice(row)"
        >
          <template #append>
            <RuiTooltip
              v-if="row.rateLimited"
              :popper="{ placement: 'top' }"
              :open-delay="400"
              tooltip-class="max-w-[16rem]"
              :disabled="refreshing"
            >
              <template #activator>
                <RuiButton
                  :disabled="!!row.price || refreshing"
                  :loading="refreshing"
                  class="-mr-3 !py-[0.625rem] rounded-l-none"
                  size="sm"
                  color="primary"
                  @click="refreshHistoricalPrice(row)"
                >
                  <RuiIcon
                    size="20"
                    name="lu-refresh-ccw"
                  />
                </RuiButton>
              </template>
              <span>
                {{ t('profit_loss_report.actionable.missing_prices.refresh_price_hint') }}
              </span>
            </RuiTooltip>
          </template>
        </AmountInput>
      </template>
    </RuiDataTable>
    <slot
      name="actions"
      :items="formattedItems"
    />
  </div>
</template>

<style module lang="scss">
.table {
  &--pinned {
    max-height: 100%;
    height: calc(100vh - 245px);
  }
}

.input {
  @apply text-left;
  min-width: 120px;
}
</style>
