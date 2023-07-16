<script setup lang="ts">
import {
  NotificationCategory,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import { type ComputedRef } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { CURRENCY_USD } from '@/types/currencies';
import { isNft } from '@/utils/nft';
import { type ManualPrice } from '@/types/prices';
import { Section } from '@/types/status';

const props = withDefaults(
  defineProps<{
    assetFilter?: string | null;
  }>(),
  {
    assetFilter: null
  }
);

const emit = defineEmits<{
  (e: 'edit', item: ManualPrice): void;
}>();

const { assetFilter } = toRefs(props);

const latestPrices = ref<ManualPrice[]>([]);
const loading = ref(false);

const { notify } = useNotificationsStore();
const { t } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'isWorth',
    sortable: false
  },
  {
    text: t('common.price'),
    value: 'price',
    align: 'end'
  },
  {
    text: t('price_table.headers.to_asset'),
    value: 'toAsset'
  },
  {
    text: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    value: 'usdPrice',
    align: 'end'
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  }
]);

const { refreshPrices } = useBalances();
const { deleteLatestPrice, fetchLatestPrices } = useAssetPricesApi();

const deletePrice = async (item: ManualPrice) => {
  const { fromAsset } = item;
  try {
    await deleteLatestPrice(fromAsset);
    await refresh();
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: t('price_table.delete.failure.title'),
      message: t('price_table.delete.failure.message', {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR,
      category: NotificationCategory.DEFAULT
    };
    notify(notification);
  }
};

const getLatestPrices = async () => {
  set(loading, true);
  try {
    set(latestPrices, await fetchLatestPrices());
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: t('price_table.fetch.failure.title'),
      message: t('price_table.fetch.failure.message', {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR,
      category: NotificationCategory.DEFAULT
    };
    notify(notification);
  } finally {
    set(loading, false);
  }
};

const { assets } = useAggregatedBalances();
const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

const refresh = async () => {
  await getLatestPrices();
  await refreshPrices(false, [...get(latestAssets), ...get(assets())]);
  await resetStatus();
};

const { assetPrice } = useBalancePricesStore();

const latestAssets: ComputedRef<string[]> = computed(() =>
  get(latestPrices)
    .flatMap(({ fromAsset, toAsset }) => [fromAsset, toAsset])
    .filter(asset => asset !== CURRENCY_USD)
);

const filteredPrices = computed(() => {
  const filter = get(assetFilter);
  const data = get(latestPrices).filter(
    ({ fromAsset }) => !filter || fromAsset === filter
  );
  return data.map(item => ({
    ...item,
    usdPrice: !isNft(item.fromAsset)
      ? get(assetPrice(item.fromAsset))
      : (get(assetPrice(item.toAsset)) ?? One).multipliedBy(item.price)
  }));
});

const { setPostSubmitFunc } = useLatestPriceForm();
onMounted(refresh);
setPostSubmitFunc(refresh);

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: ManualPrice) => {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message')
    },
    () => deletePrice(item)
  );
};
</script>

<template>
  <div>
    <VRow justify="end" class="mb-10">
      <VCol cols="auto">
        <PriceRefresh :additional-assets="latestAssets" />
      </VCol>
    </VRow>
    <Card outlined-body>
      <template #title>
        <RefreshButton
          :loading="loading"
          :tooltip="t('price_table.refresh_tooltip')"
          @refresh="refresh()"
        />
        <div>
          {{ t('price_table.latest.title') }}
        </div>
      </template>
      <slot />
      <DataTable :items="filteredPrices" :headers="headers" :loading="loading">
        <template #item.fromAsset="{ item }">
          <NftDetails
            v-if="isNft(item.fromAsset)"
            :identifier="item.fromAsset"
          />
          <AssetDetails v-else :asset="item.fromAsset" />
        </template>
        <template #item.toAsset="{ item }">
          <AssetDetails :asset="item.toAsset" />
        </template>
        <template #item.price="{ item }">
          <AmountDisplay :value="item.price" />
        </template>
        <template #item.isWorth>
          {{ t('price_table.is_worth') }}
        </template>
        <template #item.usdPrice="{ item }">
          <AmountDisplay
            v-if="item.usdPrice && item.usdPrice.gte(0)"
            show-currency="symbol"
            :price-asset="item.fromAsset"
            :price-of-asset="item.usdPrice"
            fiat-currency="USD"
            :value="item.usdPrice"
          />
          <div v-else class="d-flex justify-end">
            <VSkeletonLoader width="70" type="text" />
          </div>
        </template>
        <template #item.actions="{ item }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(item)"
            @edit-click="emit('edit', item)"
          />
        </template>
      </DataTable>
    </Card>
  </div>
</template>
