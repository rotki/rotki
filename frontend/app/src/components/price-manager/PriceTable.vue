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
      <template #item.join>{{ $t('price_table.join_text') }}</template>
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
import {
  computed,
  defineComponent,
  inject,
  onMounted,
  PropType,
  ref,
  toRef,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import { Store } from 'vuex';
import RowActions from '@/components/helper/RowActions.vue';
import i18n from '@/i18n';
import {
  HistoricalPrice,
  HistoricalPricePayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/store/notifications/consts';
import { NotificationPayload } from '@/store/notifications/types';
import { RotkehlchenState } from '@/store/types';
import { Nullable } from '@/types';
import { assert } from '@/utils/assertions';
import { nonNullProperties } from '@/utils/data';

const priceRetrieval = (store: Store<RotkehlchenState>) => {
  const prices = ref<HistoricalPrice[]>([]);
  const loading = ref(false);

  const fetchPrices = async (payload?: Partial<HistoricalPricePayload>) => {
    loading.value = true;
    try {
      prices.value = await api.assets.historicalPrices(payload);
    } catch (e) {
      const notification: NotificationPayload = {
        title: i18n.t('price_table.fetch.failure.title').toString(),
        message: i18n
          .t('price_table.fetch.failure.message', { message: e.message })
          .toString(),
        display: true,
        severity: Severity.ERROR
      };
      await store.dispatch('notifications/notify', notification);
    } finally {
      loading.value = false;
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
  const showConfirmation = computed(() => !!pending.value);

  const dismiss = () => {
    pending.value = null;
  };

  const deletePrice = async () => {
    const { price, ...payload } = pending.value!;
    pending.value = null;
    try {
      await api.assets.deleteHistoricalPrice(payload);
      await refresh();
    } catch (e) {
      const notification: NotificationPayload = {
        title: i18n.t('price_table.delete.failure.title').toString(),
        message: i18n
          .t('price_table.delete.failure.message', { message: e.message })
          .toString(),
        display: true,
        severity: Severity.ERROR
      };
      await store.dispatch('notifications/notify', notification);
    }
  };
  return {
    showConfirmation,
    pending,
    deletePrice,
    dismiss
  };
};

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
  setup(props, { emit }) {
    const store = inject<Store<RotkehlchenState>>('vuex-store');
    assert(store);
    const { fetchPrices, prices, loading } = priceRetrieval(store);
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
      await fetchPrices(filter.value);
    };

    return {
      fetchPrices,
      ...priceDeletion(store, refresh),
      prices,
      loading
    };
  },
  data() {
    return {
      headers: [
        {
          text: this.$t('price_table.headers.from_asset').toString(),
          value: 'fromAsset'
        },
        {
          text: '',
          value: 'join'
        },
        {
          text: this.$t('price_table.headers.price').toString(),
          value: 'price'
        },
        {
          text: this.$t('price_table.headers.to_asset').toString(),
          value: 'toAsset'
        },
        {
          text: this.$t('price_table.headers.date').toString(),
          value: 'timestamp'
        },
        {
          text: '',
          value: 'actions'
        }
      ] as DataTableHeader[]
    };
  }
});
</script>

<style scoped></style>
