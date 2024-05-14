<script setup lang="ts">
import { isNft } from '@/utils/nft';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { ManualPrice, ManualPriceFormPayload } from '@/types/prices';

const { t } = useI18n();

const price: Ref<Partial<ManualPriceFormPayload> | null> = ref(null);
const filter = ref<string>();
const editMode: Ref<boolean> = ref(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const sort: Ref<DataTableSortData> = ref([]);

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('price_table.headers.from_asset'),
    key: 'fromAsset',
    sortable: true,
  },
  {
    label: '',
    key: 'isWorth',
    cellClass: '!text-xs !text-rui-text-secondary',
  },
  {
    label: t('common.price'),
    key: 'price',
    align: 'end',
    sortable: true,
  },
  {
    label: t('price_table.headers.to_asset'),
    key: 'toAsset',
    sortable: true,
  },
  {
    label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    key: 'usdPrice',
    align: 'end',
    sortable: true,
  },
  {
    label: '',
    key: 'actions',
    class: 'w-[3rem]',
    align: 'end',
  },
]);

const router = useRouter();
const route = useRoute();
const {
  items,
  loading,
  refreshing,
  deletePrice,
  refreshCurrentPrices,
} = useLatestPrices(t, filter);

const { setPostSubmitFunc, setOpenDialog } = useLatestPriceForm();
const { show } = useConfirmStore();

function showDeleteConfirmation(item: ManualPrice) {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message'),
    },
    () => deletePrice(item),
  );
}

function openForm(selectedEntry: ManualPrice | null = null) {
  set(editMode, !!selectedEntry);
  if (selectedEntry) {
    set(price, {
      ...selectedEntry,
      price: selectedEntry.price.toFixed() ?? '',
    });
  }
  else {
    set(price, {
      fromAsset: get(filter) ?? '',
    });
  }
  setOpenDialog(true);
}

onMounted(async () => {
  await refreshCurrentPrices();
  setPostSubmitFunc(() => refreshCurrentPrices());

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
      t('navigation_menu.manage_prices_sub.latest_prices'),
    ]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading || refreshing"
            @click="refreshCurrentPrices()"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('price_table.refresh_tooltip') }}
      </RuiTooltip>

      <RuiButton
        color="primary"
        @click="openForm()"
      >
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
            <RuiIcon
              size="20"
              name="filter-line"
            />
          </template>
        </AssetSelect>
      </div>
      <RuiDataTable
        outlined
        dense
        :cols="headers"
        :loading="loading || refreshing"
        :rows="items"
        row-attr="id"
        :sort.sync="sort"
      >
        <template #item.fromAsset="{ row }">
          <NftDetails
            v-if="isNft(row.fromAsset)"
            :identifier="row.fromAsset"
          />
          <AssetDetails
            v-else
            class="[&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
            :asset="row.fromAsset"
          />
        </template>
        <template #item.toAsset="{ row }">
          <AssetDetails :asset="row.toAsset" />
        </template>
        <template #item.price="{ row }">
          <AmountDisplay :value="row.price" />
        </template>
        <template #item.isWorth>
          {{ t('price_table.is_worth') }}
        </template>
        <template #item.usdPrice="{ row }">
          <AmountDisplay
            :loading="!row.usdPrice || row.usdPrice.lt(0)"
            show-currency="symbol"
            :price-asset="row.fromAsset"
            :price-of-asset="row.usdPrice"
            fiat-currency="USD"
            :value="row.usdPrice"
          />
        </template>
        <template #item.actions="{ row }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="openForm(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <LatestPriceFormDialog
      :value="price"
      :edit-mode="editMode"
    />
  </TablePageLayout>
</template>
