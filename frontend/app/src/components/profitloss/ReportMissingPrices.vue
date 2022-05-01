<template>
  <div>
    <data-table
      :class="$style.table"
      :headers="headers"
      :items="formattedItems"
    >
      <template #item="{ item }">
        <tr :key="item.fromAsset + item.toAsset + item.time">
          <td>
            <asset-details :asset="item.fromAsset" />
          </td>
          <td>
            <asset-details :asset="item.toAsset" />
          </td>
          <td>
            <date-display :timestamp="item.time" />
          </td>
          <td class="py-3">
            <amount-input
              v-model="item.price"
              dense
              placeholder="Input price"
              outlined
              :success-messages="
                item.saved
                  ? [
                      $tc(
                        'profit_loss_report.actionable.missing_prices.price_is_saved'
                      )
                    ]
                  : []
              "
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
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import i18n from '@/i18n';
import {
  HistoricalPrice,
  HistoricalPriceDeletePayload,
  HistoricalPriceFormPayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { MissingPrice } from '@/types/reports';

export type EditableMissingPrice = MissingPrice & {
  price: string;
  saved: boolean;
};

export default defineComponent({
  name: 'ReportMissingPrices',
  props: {
    items: { required: true, type: Array as PropType<MissingPrice[]> }
  },
  setup(props) {
    const { items } = toRefs(props);
    const prices = ref<HistoricalPrice[]>([]);

    const fetchHistoricalPrices = async () => {
      set(prices, await api.assets.historicalPrices());
    };

    onMounted(async () => {
      await fetchHistoricalPrices();
    });

    const headers = computed<DataTableHeader[]>(() => {
      return [
        {
          text: i18n
            .t(
              'profit_loss_report.actionable.missing_prices.headers.from_asset'
            )
            .toString(),
          value: 'fromAsset'
        },
        {
          text: i18n
            .t('profit_loss_report.actionable.missing_prices.headers.to_asset')
            .toString(),
          value: 'toAsset'
        },
        {
          text: i18n
            .t('profit_loss_report.actionable.missing_prices.headers.time')
            .toString(),
          value: 'time'
        },
        {
          text: i18n
            .t('profit_loss_report.actionable.missing_prices.headers.price')
            .toString(),
          value: 'price',
          sortable: false
        }
      ];
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
          price: savedHistoricalPrice?.price?.toString() ?? ''
        };
      });
    });

    const updatePrice = async (item: EditableMissingPrice) => {
      const payload: HistoricalPriceDeletePayload = {
        fromAsset: item.fromAsset,
        toAsset: item.toAsset,
        timestamp: item.time
      };

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

      await fetchHistoricalPrices();
    };

    return {
      updatePrice,
      formattedItems,
      headers
    };
  }
});
</script>

<style module lang="scss">
.table {
  max-height: calc(100vh - 350px);
  overflow: auto;
}
</style>
