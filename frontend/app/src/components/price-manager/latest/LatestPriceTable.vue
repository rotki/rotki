<template>
  <div>
    <v-row justify="end" class="mb-10">
      <v-col cols="auto">
        <price-refresh :additional-assets="latestAssets" />
      </v-col>
    </v-row>
    <card outlined-body>
      <template #title>
        <refresh-button
          :loading="loading"
          :tooltip="tc('price_table.refresh_tooltip')"
          @refresh="refresh"
        />
        <div>
          {{ tc('price_table.latest.title') }}
        </div>
      </template>
      <slot />
      <data-table :items="filteredPrices" :headers="headers" :loading="loading">
        <template #item.fromAsset="{ item }">
          <asset-details :asset="item.fromAsset" />
        </template>
        <template #item.toAsset="{ item }">
          <asset-details :asset="item.toAsset" />
        </template>
        <template #item.price="{ item }">
          <amount-display :value="item.price" />
        </template>
        <template #item.isWorth>
          {{ tc('price_table.is_worth') }}
        </template>
        <template #item.usdPrice="{ item }">
          <amount-display
            v-if="item.usdPrice && item.usdPrice.gte(0)"
            show-currency="symbol"
            :price-asset="item.fromAsset"
            :price-of-asset="item.usdPrice"
            fiat-currency="USD"
            :value="item.usdPrice"
          />
          <div v-else class="d-flex justify-end">
            <v-skeleton-loader width="70" type="text" />
          </div>
        </template>
        <template #item.actions="{ item }">
          <row-actions
            :disabled="loading"
            :delete-tooltip="tc('price_table.actions.delete.tooltip')"
            :edit-tooltip="tc('price_table.actions.edit.tooltip')"
            @delete-click="pending = item"
            @edit-click="$emit('edit', item)"
          />
        </template>
      </data-table>
      <confirm-dialog
        :title="tc('price_table.delete.dialog.title')"
        :message="tc('price_table.delete.dialog.message')"
        :display="showConfirmation"
        @confirm="deletePrice"
        @cancel="dismiss"
      />
    </card>
  </div>
</template>

<script setup lang="ts">
import { NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { ComputedRef, PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { ManualPrice } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useBalancesStore } from '@/store/balances';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Nullable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import { isNft } from '@/utils/nft';

const props = defineProps({
  assetFilter: {
    type: String as PropType<string | null>,
    required: false,
    default: null
  },
  refreshing: {
    type: Boolean,
    required: false,
    default: false
  }
});

const emit = defineEmits(['edit', 'refreshed']);
const { assetFilter, refreshing } = toRefs(props);

const latestPrices = ref<ManualPrice[]>([]);
const loading = ref(false);
const pending = ref<Nullable<ManualPrice>>(null);
const showConfirmation = computed(() => !!get(pending));

const { notify } = useNotifications();
const { tc } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const headers = computed<DataTableHeader[]>(() => [
  {
    text: tc('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'isWorth',
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
    text: tc('common.price_in_symbol', 0, { symbol: get(currencySymbol) }),
    value: 'usdPrice',
    align: 'end'
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  }
]);

const dismiss = () => {
  set(pending, null);
};

const { refreshPrices } = useBalancesStore();

const deletePrice = async () => {
  const { fromAsset } = get(pending)!;
  set(pending, null);
  try {
    await api.assets.deleteLatestPrice(fromAsset);
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

const fetchLatestPrices = async () => {
  set(loading, true);
  try {
    set(latestPrices, await api.assets.fetchLatestPrices());
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

const { assets } = useAggregatedBalancesStore();

const refresh = async () => {
  await fetchLatestPrices();
  await refreshPrices(false, [...get(latestAssets), ...get(assets())]);
};

const { assetPrice } = useBalancePricesStore();

const latestAssets: ComputedRef<string[]> = computed(() => {
  return get(latestPrices)
    .map(({ fromAsset, toAsset }) => [fromAsset, toAsset])
    .flat()
    .filter(asset => asset !== CURRENCY_USD);
});

const filteredPrices = computed(() => {
  const filter = get(assetFilter);
  const data = get(latestPrices).filter(({ fromAsset }) => {
    return !isNft(fromAsset) && (!filter || fromAsset === filter);
  });
  return data.map(item => ({
    ...item,
    usdPrice: get(assetPrice(item.fromAsset))
  }));
});

watch(refreshing, async refreshing => {
  if (!refreshing) {
    return;
  }
  await refresh();
  emit('refreshed');
});

onMounted(refresh);
</script>
