<template>
  <div>
    <data-table
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
            <asset-details :asset="item.fromAsset" />
          </td>
          <td :class="isPinned ? 'px-2' : ''">
            <asset-details :asset="item.toAsset" />
          </td>
          <td :class="isPinned ? 'px-2' : ''">
            <date-display :timestamp="item.time" />
          </td>
          <td :class="isPinned ? 'px-2 py-1' : 'py-3'">
            <amount-input
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
                      tc(
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
                <v-tooltip
                  v-if="item.rateLimited"
                  bottom
                  max-width="300"
                  :disabled="refreshing"
                >
                  <template #activator="{ on }">
                    <v-btn
                      :disabled="!!item.price || refreshing"
                      :loading="refreshing"
                      class="mr-n3"
                      depressed
                      height="100%"
                      color="primary"
                      v-on="on"
                      @click="() => refreshHistoricalPrice(item)"
                    >
                      <v-icon>mdi-refresh</v-icon>
                    </v-btn>
                  </template>
                  <span>
                    {{
                      t(
                        'profit_loss_report.actionable.missing_prices.refresh_price_hint'
                      )
                    }}
                  </span>
                </v-tooltip>
              </template>
            </amount-input>
          </td>
        </tr>
      </template>
    </data-table>
    <slot name="actions" :items="formattedItems" />
  </div>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { PropType, Ref } from 'vue';
import { DataTableHeader } from 'vuetify';
import {
  HistoricalPrice,
  HistoricalPriceDeletePayload,
  HistoricalPriceFormPayload
} from '@/services/assets/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import { useBalancePricesStore } from '@/store/balances/prices';
import { EditableMissingPrice } from '@/types/prices';
import { MissingPrice } from '@/types/reports';

const props = defineProps({
  items: { required: true, type: Array as PropType<MissingPrice[]> },
  isPinned: { required: true, type: Boolean, default: false }
});

const { t, tc } = useI18n();
const { items } = toRefs(props);
const prices = ref<HistoricalPrice[]>([]);
const errorMessages: Ref<Record<string, string[]>> = ref({});

const createKey = (item: MissingPrice) => {
  return item.fromAsset + item.toAsset + item.time;
};

const fetchHistoricalPrices = async () => {
  set(prices, await api.assets.historicalPrices());
};

onMounted(async () => {
  await fetchHistoricalPrices();
});

const refreshedHistoricalPrices: Ref<Record<string, BigNumber>> = ref({});

const formattedItems = computed<EditableMissingPrice[]>(() => {
  return get(items).map(item => {
    const savedHistoricalPrice = get(prices).find(price => {
      return (
        price.fromAsset === item.fromAsset &&
        price.toAsset === item.toAsset &&
        price.timestamp === item.time
      );
    });

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
  });
});

const updatePrice = async (item: EditableMissingPrice) => {
  if (item.useRefreshedHistoricalPrice) return;

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
        await api.assets.editHistoricalPrice(formPayload);
      } else {
        await api.assets.addHistoricalPrice(formPayload);
      }
    } else {
      if (item.saved) {
        await api.assets.deleteHistoricalPrice(payload);
      }
    }
  } catch (e: any) {
    const message = deserializeApiErrorMessage(e.message) as any;
    const errorMessage = message ? message.price[0] : e.message;

    set(errorMessages, {
      ...get(errorMessages),
      [createKey(item)]: errorMessage
    });
  }

  await fetchHistoricalPrices();
};

const tableRef = ref<any>(null);

const tableContainer = computed(() => {
  return get(tableRef)?.$el;
});

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
