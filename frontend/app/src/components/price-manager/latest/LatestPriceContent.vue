<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { isNft } from '@/utils/nft';
import { type ManualPrice, type ManualPriceFormPayload } from '@/types/prices';
import { type Nullable } from '@/types';

const { t } = useI18n();

const price: Ref<Partial<ManualPriceFormPayload> | null> = ref(null);
const filter: Ref<Nullable<string>> = ref(null);
const editMode: Ref<boolean> = ref(false);

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

const router = useRouter();
const route = useRoute();
const {
  items,
  loading,
  refreshing,
  deletePrice,
  refreshCurrentPrices,
  getLatestPrices
} = useLatestPrices(t, filter);

const { setPostSubmitFunc, setOpenDialog } = useLatestPriceForm();
const { show } = useConfirmStore();

const showDeleteConfirmation = (item: ManualPrice) => {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message')
    },
    () => deletePrice(item, true)
  );
};

const openForm = (selectedEntry: ManualPrice | null = null) => {
  set(editMode, !!selectedEntry);
  if (selectedEntry) {
    set(price, {
      ...selectedEntry,
      price: selectedEntry.price.toFixed() ?? ''
    });
  } else {
    set(price, {
      fromAsset: get(filter) ?? ''
    });
  }
  setOpenDialog(true);
};

const refreshDataAndPrices = async (refresh = false) => {
  await getLatestPrices();
  await refreshCurrentPrices(refresh);
};

onMounted(async () => {
  await refreshDataAndPrices();
  setPostSubmitFunc(() => refreshDataAndPrices(true));

  const query = get(route).query;

  if (query.add) {
    openForm();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_prices'),
      t('navigation_menu.manage_prices_sub.latest_prices')
    ]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading || refreshing"
            @click="refreshDataAndPrices(true)"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('price_table.refresh_tooltip') }}
      </RuiTooltip>

      <RuiButton color="primary" @click="openForm()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('price_management.dialog.add_title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="mb-4 flex flex-row-reverse">
        <AssetSelect
          v-model="filter"
          class="max-w-[360px]"
          outlined
          include-nfts
          :label="t('price_management.from_asset')"
          clearable
          hide-details
        >
          <template #prepend>
            <RuiIcon size="20" name="filter-line" />
          </template>
        </AssetSelect>
      </div>
      <DataTable :items="items" :headers="headers" :loading="loading">
        <template #item.fromAsset="{ item }">
          <NftDetails
            v-if="isNft(item.fromAsset)"
            :identifier="item.fromAsset"
          />
          <AssetDetails
            v-else
            class="max-w-[20rem] [&>span>div]:pl-2.5 [&>span>div]:pr-1.5"
            :asset="item.fromAsset"
          />
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
            :loading="!item.usdPrice || item.usdPrice.lt(0)"
            show-currency="symbol"
            :price-asset="item.fromAsset"
            :price-of-asset="item.usdPrice"
            fiat-currency="USD"
            :value="item.usdPrice"
          />
        </template>
        <template #item.actions="{ item }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(item)"
            @edit-click="openForm(item)"
          />
        </template>
      </DataTable>
    </RuiCard>

    <LatestPriceFormDialog :value="price" :edit-mode="editMode" />
  </TablePageLayout>
</template>
