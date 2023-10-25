<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type EditableMissingPrice, type MissingPrice } from '@/types/reports';
import {
  type HistoricalPrice,
  type HistoricalPriceDeletePayload,
  type HistoricalPriceFormPayload
} from '@/types/prices';
import { ApiValidationError } from '@/types/api/errors';

const props = defineProps<{
  items: MissingPrice[];
  isPinned: boolean;
}>();

const { t } = useI18n();
const { items } = toRefs(props);
const prices = ref<HistoricalPrice[]>([]);
const errorMessages: Ref<Record<string, string[]>> = ref({});
const {
  fetchHistoricalPrices,
  addHistoricalPrice,
  editHistoricalPrice,
  deleteHistoricalPrice
} = useAssetPricesApi();

const createKey = (item: MissingPrice) =>
  item.fromAsset + item.toAsset + item.time;

const getHistoricalPrices = async () => {
  set(prices, await fetchHistoricalPrices());
};

onMounted(async () => {
  await getHistoricalPrices();
});

const refreshedHistoricalPrices: Ref<Record<string, BigNumber>> = ref({});

const formattedItems = computed<EditableMissingPrice[]>(() =>
  get(items).map(item => {
    const savedHistoricalPrice = get(prices).find(
      price =>
        price.fromAsset === item.fromAsset &&
        price.toAsset === item.toAsset &&
        price.timestamp === item.time
    );

    const key = createKey(item);
    const savedPrice = savedHistoricalPrice?.price;
    const refreshedHistoricalPrice = get(refreshedHistoricalPrices)[key];

    const useRefreshedHistoricalPrice =
      !savedPrice && !!refreshedHistoricalPrice;

    const price =
      (useRefreshedHistoricalPrice
        ? refreshedHistoricalPrice
        : savedPrice
      )?.toFixed() ?? '';

    return {
      ...item,
      saved: !!savedPrice,
      price,
      useRefreshedHistoricalPrice
    };
  })
);

const updatePrice = async (item: EditableMissingPrice) => {
  if (item.useRefreshedHistoricalPrice) {
    return;
  }

  const payload: HistoricalPriceDeletePayload = {
    fromAsset: item.fromAsset,
    toAsset: item.toAsset,
    timestamp: item.time
  };

  try {
    if (item.price) {
      const formPayload: HistoricalPriceFormPayload = {
        ...payload,
        price: item.price
      };

      if (item.saved) {
        await editHistoricalPrice(formPayload);
      } else {
        await addHistoricalPrice(formPayload);
      }
    } else if (item.saved) {
      await deleteHistoricalPrice(payload);
    }
  } catch (e: any) {
    let errorMessage = e.message;
    if (e instanceof ApiValidationError) {
      const errors = e.getValidationErrors({ price: '' });
      errorMessage = typeof errors === 'string' ? e.message : errors.price[0];
    }

    set(errorMessages, {
      ...get(errorMessages),
      [createKey(item)]: errorMessage
    });
  }

  await getHistoricalPrices();
};

const tableRef = ref<any>(null);

const tableContainer = computed(() => get(tableRef)?.$el);

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t(
      'profit_loss_report.actionable.missing_prices.headers.from_asset'
    ).toString(),
    value: 'fromAsset'
  },
  {
    text: t(
      'profit_loss_report.actionable.missing_prices.headers.to_asset'
    ).toString(),
    value: 'toAsset'
  },
  {
    text: t('common.datetime').toString(),
    value: 'time'
  },
  {
    text: t('common.price').toString(),
    value: 'price',
    sortable: false
  }
]);

const { getHistoricPrice } = useBalancePricesStore();

const refreshing = ref<boolean>(false);

const refreshHistoricalPrice = async (item: EditableMissingPrice) => {
  set(refreshing, true);
  const rateFromHistoricPrice = await getHistoricPrice({
    timestamp: item.time,
    fromAsset: item.fromAsset,
    toAsset: item.toAsset
  });

  const key = createKey(item);
  if (rateFromHistoricPrice && rateFromHistoricPrice.gt(0)) {
    const refreshedHistoricalPricesVal = get(refreshedHistoricalPrices);
    refreshedHistoricalPricesVal[key] = rateFromHistoricPrice;
    set(refreshedHistoricalPrices, refreshedHistoricalPricesVal);
  } else {
    set(errorMessages, {
      ...get(errorMessages),
      [key]: t('profit_loss_report.actionable.missing_prices.price_not_found')
    });
  }
  set(refreshing, false);
};
</script>

<template>
  <div>
    <DataTable
      ref="tableRef"
      class="table-inside-dialog"
      :class="{
        [$style['table--pinned']]: isPinned
      }"
      :headers="headers"
      :items="formattedItems"
      :container="tableContainer"
      :dense="isPinned"
    >
      <template #item="{ item }">
        <tr :key="createKey(item)">
          <td :class="isPinned ? 'px-2' : ''">
            <AssetDetails link :asset="item.fromAsset" />
          </td>
          <td :class="isPinned ? 'px-2' : ''">
            <AssetDetails link :asset="item.toAsset" />
          </td>
          <td :class="isPinned ? 'px-2' : ''">
            <DateDisplay :timestamp="item.time" />
          </td>
          <td :class="isPinned ? 'px-2 py-1' : 'py-3'">
            <AmountInput
              v-model="item.price"
              :class="$style.input"
              class="mb-n2"
              dense
              :disabled="item.useRefreshedHistoricalPrice"
              :placeholder="
                t('profit_loss_report.actionable.missing_prices.input_price')
              "
              outlined
              :success-messages="
                item.saved
                  ? [
                      t(
                        'profit_loss_report.actionable.missing_prices.price_is_saved'
                      )
                    ]
                  : []
              "
              :error-messages="errorMessages[createKey(item)]"
              @focus="delete errorMessages[createKey(item)]"
              @input="delete errorMessages[createKey(item)]"
              @blur="updatePrice(item)"
            >
              <template #append>
                <VTooltip
                  v-if="item.rateLimited"
                  bottom
                  max-width="300"
                  :disabled="refreshing"
                >
                  <template #activator="{ on }">
                    <VBtn
                      :disabled="!!item.price || refreshing"
                      :loading="refreshing"
                      class="mr-n3"
                      depressed
                      height="100%"
                      color="primary"
                      v-on="on"
                      @click="refreshHistoricalPrice(item)"
                    >
                      <RuiIcon name="refresh-line" />
                    </VBtn>
                  </template>
                  <span>
                    {{
                      t(
                        'profit_loss_report.actionable.missing_prices.refresh_price_hint'
                      )
                    }}
                  </span>
                </VTooltip>
              </template>
            </AmountInput>
          </td>
        </tr>
      </template>
    </DataTable>
    <slot name="actions" :items="formattedItems" />
  </div>
</template>

<style module lang="scss">
.table {
  &--pinned {
    max-height: 100%;
    height: calc(100vh - 230px);
  }
}

.input {
  min-width: 150px;

  :global {
    .v-input {
      &__append-inner {
        display: flex !important;
        align-self: stretch !important;
        align-items: center;
        margin-top: 0 !important;
      }
    }
  }
}
</style>
