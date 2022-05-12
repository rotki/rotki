<template>
  <card outlined-body>
    <template #title>{{ $t('price_table.title') }}</template>
    <slot />
    <data-table
      :items="prices"
      :headers="headers"
      :loading="loading"
      sort-by="timestamp"
    >
      <template #item.fromAsset="{ item }">
        <asset-details :asset="item.fromAsset" />
      </template>
      <template #item.toAsset="{ item }">
        <asset-details :asset="item.toAsset" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.price="{ item }">
        <amount-display :value="item.price" />
      </template>
      <template #item.wasWorth>{{ $t('price_table.was_worth') }}</template>
      <template #item.on>{{ $t('price_table.on') }}</template>
      <template #item.actions="{ item }">
        <row-actions
          :disabled="loading"
          :delete-tooltip="$t('price_table.actions.delete.tooltip')"
          :edit-tooltip="$t('price_table.actions.edit.tooltip')"
          @delete-click="pending = item"
          @edit-click="$emit('edit', item)"
        />
      </template>
    </data-table>
    <confirm-dialog
      :title="$t('price_table.delete.dialog.title')"
      :message="$t('price_table.delete.dialog.message')"
      :display="showConfirmation"
      @confirm="deletePrice"
      @cancel="dismiss"
    />
  </card>
</template>

<script lang="ts">
import { NotificationPayload, Severity } from '@rotki/common/lib/messages';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRef,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import { Store } from 'vuex';
import RowActions from '@/components/helper/RowActions.vue';
import i18n from '@/i18n';
import {
  HistoricalPrice,
  HistoricalPricePayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { Nullable } from '@/types';
import { nonNullProperties } from '@/utils/data';

const priceRetrieval = () => {
  const prices = ref<HistoricalPrice[]>([]);
  const loading = ref(false);

  const { notify } = useNotifications();

  const fetchPrices = async (payload?: Partial<HistoricalPricePayload>) => {
    set(loading, true);
    try {
      set(prices, await api.assets.historicalPrices(payload));
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: i18n.t('price_table.fetch.failure.title').toString(),
        message: i18n
          .t('price_table.fetch.failure.message', { message: e.message })
          .toString(),
        display: true,
        severity: Severity.ERROR
      };
      notify(notification);
    } finally {
      set(loading, false);
    }
  };
  onMounted(fetchPrices);
  return {
    loading,
    prices,
    fetchPrices
  };
};

const priceDeletion = (
  store: Store<RotkehlchenState>,
  refresh: () => Promise<void>
) => {
  const pending = ref<Nullable<HistoricalPrice>>(null);
  const showConfirmation = computed(() => !!get(pending));

  const dismiss = () => {
    set(pending, null);
  };

  const { notify } = useNotifications();

  const deletePrice = async () => {
    const { price, ...payload } = get(pending)!;
    set(pending, null);
    try {
      await api.assets.deleteHistoricalPrice(payload);
      await refresh();
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: i18n.t('price_table.delete.failure.title').toString(),
        message: i18n
          .t('price_table.delete.failure.message', { message: e.message })
          .toString(),
        display: true,
        severity: Severity.ERROR
      };
      notify(notification);
    }
  };
  return {
    showConfirmation,
    pending,
    deletePrice,
    dismiss
  };
};

const headers: DataTableHeader[] = [
  {
    text: i18n.t('price_table.headers.from_asset').toString(),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'wasWorth'
  },
  {
    text: i18n.t('price_table.headers.price').toString(),
    value: 'price'
  },
  {
    text: i18n.t('price_table.headers.to_asset').toString(),
    value: 'toAsset'
  },
  {
    text: '',
    value: 'on'
  },
  {
    text: i18n.t('price_table.headers.date').toString(),
    value: 'timestamp'
  },
  {
    text: '',
    value: 'actions'
  }
];

export default defineComponent({
  name: 'PriceTable',
  components: { RowActions },
  props: {
    filter: {
      type: Object as PropType<HistoricalPricePayload>,
      required: true
    },
    refresh: {
      type: Boolean,
      required: false,
      default: false
    }
  },
  emits: ['edit', 'refreshed'],
  setup(props, { emit }) {
    const store = useStore();
    const { fetchPrices, prices, loading } = priceRetrieval();
    watch(props.filter, async payload => {
      await fetchPrices(nonNullProperties(payload));
    });
    watch(
      () => props.refresh,
      async refresh => {
        if (!refresh) {
          return;
        }
        await fetchPrices();
        emit('refreshed');
      }
    );

    const filter = toRef(props, 'filter');
    const refresh = async () => {
      await fetchPrices(get(filter));
    };

    return {
      fetchPrices,
      ...priceDeletion(store, refresh),
      headers,
      prices,
      loading
    };
  }
});
</script>
