<script setup lang="ts">
import { type NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { type PropType } from 'vue';
import { type DataTableHeader } from 'vuetify';
import RowActions from '@/components/helper/RowActions.vue';
import {
  type HistoricalPrice,
  type ManualPricePayload
} from '@/services/assets/types';
import { useNotificationsStore } from '@/store/notifications';
import { useAssetPricesApi } from '@/services/assets/prices';
import { useConfirmStore } from '@/store/confirm';

const props = defineProps({
  filter: {
    type: Object as PropType<ManualPricePayload>,
    required: true
  },
  refreshing: {
    type: Boolean,
    required: false,
    default: false
  }
});

const emit = defineEmits(['edit', 'refreshed']);
const { filter, refreshing } = toRefs(props);

const prices = ref<HistoricalPrice[]>([]);
const loading = ref(false);

const { notify } = useNotificationsStore();
const { tc } = useI18n();
const { deleteHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: tc('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'wasWorth',
    sortable: false
  },
  {
    text: tc('common.price'),
    value: 'price',
    align: 'end'
  },
  {
    text: tc('price_table.headers.to_asset'),
    value: 'toAsset'
  },
  {
    text: '',
    value: 'on',
    sortable: false
  },
  {
    text: tc('common.datetime'),
    value: 'timestamp'
  },
  {
    text: '',
    value: 'actions'
  }
]);

const deletePrice = async (item: HistoricalPrice) => {
  const { price, ...payload } = item!;
  try {
    await deleteHistoricalPrice(payload);
    await refresh();
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: tc('price_table.delete.failure.title'),
      message: tc('price_table.delete.failure.message', 0, {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR
    };
    notify(notification);
  }
};

const fetchPrices = async (payload?: Partial<ManualPricePayload>) => {
  set(loading, true);
  try {
    set(prices, await fetchHistoricalPrices(payload));
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: tc('price_table.fetch.failure.title'),
      message: tc('price_table.fetch.failure.message', 0, {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR
    };
    notify(notification);
  } finally {
    set(loading, false);
  }
};

const refresh = async () => {
  await fetchPrices(get(filter));
};

watch(
  filter,
  async () => {
    await refresh();
  },
  { deep: true }
);

watch(refreshing, async refreshing => {
  if (!refreshing) {
    return;
  }
  await refresh();
  emit('refreshed');
});

onMounted(fetchPrices);

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: HistoricalPrice) => {
  show(
    {
      title: tc('price_table.delete.dialog.title'),
      message: tc('price_table.delete.dialog.message')
    },
    () => deletePrice(item)
  );
};
</script>

<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="tc('price_table.refresh_tooltip')"
        @refresh="refresh"
      />
      <div>
        {{ tc('price_table.historic.title') }}
      </div>
    </template>
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
      <template #item.wasWorth>{{ tc('price_table.was_worth') }}</template>
      <template #item.on>{{ tc('price_table.on') }}</template>
      <template #item.actions="{ item }">
        <row-actions
          :disabled="loading"
          :delete-tooltip="tc('price_table.actions.delete.tooltip')"
          :edit-tooltip="tc('price_table.actions.edit.tooltip')"
          @delete-click="showDeleteConfirmation(item)"
          @edit-click="$emit('edit', item)"
        />
      </template>
    </data-table>
  </card>
</template>
