<template>
  <div>
    <data-table
      ref="tableRef"
      :class="{
        [$style.table]: true,
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
              placeholder="Input price"
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
              @blur="updatePrice(item)"
            />
          </td>
        </tr>
      </template>
    </data-table>
    <slot name="actions" :items="formattedItems" />
  </div>
</template>
<script lang="ts">
import { get, set } from '@vueuse/core';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  Ref,
  ref,
  toRefs
} from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { DataTableHeader } from 'vuetify';
import {
  HistoricalPrice,
  HistoricalPriceDeletePayload,
  HistoricalPriceFormPayload
} from '@/services/assets/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import { MissingPrice } from '@/types/reports';

export type EditableMissingPrice = MissingPrice & {
  price: string;
  saved: boolean;
};

export default defineComponent({
  name: 'ReportMissingPrices',
  props: {
    items: { required: true, type: Array as PropType<MissingPrice[]> },
    isPinned: { required: true, type: Boolean, default: false }
  },
  setup(props) {
    const { t, tc } = useI18n();
    const { items } = toRefs(props);
    const prices = ref<HistoricalPrice[]>([]);
    const errorMessages: Ref<{ [key: string]: string[] }> = ref({});

    const createKey = (item: MissingPrice) => {
      return item.fromAsset + item.toAsset + item.time;
    };

    const fetchHistoricalPrices = async () => {
      set(prices, await api.assets.historicalPrices());
    };

    onMounted(async () => {
      await fetchHistoricalPrices();
    });

    const formattedItems = computed<EditableMissingPrice[]>(() => {
      return get(items).map(item => {
        const savedHistoricalPrice = get(prices).find(price => {
          return (
            price.fromAsset === item.fromAsset &&
            price.toAsset === item.toAsset &&
            price.timestamp === item.time
          );
        });

        return {
          ...item,
          saved: !!savedHistoricalPrice?.price,
          price: savedHistoricalPrice?.price?.toFixed() ?? ''
        };
      });
    });

    const updatePrice = async (item: EditableMissingPrice) => {
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

    return {
      t,
      tc,
      headers,
      updatePrice,
      formattedItems,
      errorMessages,
      createKey,
      tableRef,
      tableContainer
    };
  }
});
</script>

<style module lang="scss">
.table {
  scroll-behavior: smooth;
  max-height: calc(100vh - 310px);
  overflow: auto;

  &--pinned {
    max-height: 100%;
    height: calc(100vh - 230px);
  }
}

.input {
  min-width: 150px;
}
</style>
