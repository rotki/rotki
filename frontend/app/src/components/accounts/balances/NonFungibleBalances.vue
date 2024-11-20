<script setup lang="ts">
import { Section } from '@/types/status';
import type { DataTableColumn } from '@rotki/ui-library';
import type { ActionStatus } from '@/types/action';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { Module } from '@/types/modules';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import type { ManualPriceFormPayload } from '@/types/prices';
import type { BigNumber } from '@rotki/common';

defineProps<{ modules: Module[] }>();

const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNonFungibleBalancesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();
const { notify } = useNotificationsStore();
const { deleteLatestPrice } = useAssetPricesApi();

const customPrice = ref<Partial<ManualPriceFormPayload> | null>(null);

const selected = ref<string[]>([]);
const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');

const extraParams = computed(() => ({
  ignoredAssetsHandling: get(ignoredAssetsHandling),
}));

const tableHeaders = computed<DataTableColumn<NonFungibleBalance>[]>(() => [
  {
    label: t('common.name'),
    key: 'name',
    cellClass: 'text-no-wrap',
    sortable: true,
  },
  {
    label: t('non_fungible_balances.ignore'),
    key: 'ignored',
    align: 'center',
    sortable: false,
  },
  {
    label: t('non_fungible_balances.column.price_in_asset'),
    key: 'priceInAsset',
    align: 'end',
    width: '75%',
    class: 'text-no-wrap',
    sortable: false,
  },
  {
    label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    key: 'usdPrice',
    align: 'end',
    class: 'text-no-wrap',
    sortable: true,
  },
  {
    label: t('non_fungible_balances.column.custom_price'),
    key: 'manuallyInput',
    class: 'text-no-wrap',
    sortable: false,
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    align: 'center',
    sortable: false,
    width: '50',
  },
]);

const { isLoading: isSectionLoading } = useStatusStore();
const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();
const { assetPrice } = useBalancePricesStore();

const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

const {
  state: balances,
  isLoading,
  fetchData,
  sort,
  setPage,
  pagination,
} = usePaginationFilters<
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload
>(fetchNonFungibleBalances, {
  history: 'router',
  onUpdateFilters(query) {
    set(ignoredAssetsHandling, query.ignoredAssetsHandling || 'exclude');
  },
  extraParams,
  defaultSortBy: [{
    column: 'usdPrice',
    direction: 'desc',
  }],
});

const { setPostSubmitFunc, setOpenDialog } = useLatestPriceForm();
const { show } = useConfirmStore();

const isIgnored = (identifier: string) => isAssetIgnored(identifier);

async function toggleIgnoreAsset(identifier: string) {
  let success;
  if (get(isIgnored(identifier))) {
    const response = await unignoreAsset(identifier);
    success = response.success;
  }
  else {
    const response = await ignoreAsset(identifier);
    success = response.success;
  }

  if (success && get(ignoredAssetsHandling) !== 'none')
    await fetchData();
}

async function massIgnore(ignored: boolean) {
  const ids = get(selected)
    .filter((item) => {
      const isItemIgnored = get(isIgnored(item));
      return ignored ? !isItemIgnored : isItemIgnored;
    })
    .filter(uniqueStrings);

  let status: ActionStatus;

  if (ids.length === 0) {
    const choice = ignored ? 1 : 2;
    setMessage({
      success: false,
      title: t('ignore.no_items.title', choice),
      description: t('ignore.no_items.description', choice),
    });
    return;
  }

  if (ignored)
    status = await ignoreAsset(ids);
  else status = await unignoreAsset(ids);

  if (status.success) {
    set(selected, []);
    if (get(ignoredAssetsHandling) !== 'none')
      await fetchData();
  }
}

async function deletePrice(toDeletePrice: NonFungibleBalance) {
  try {
    await deleteLatestPrice(toDeletePrice.id);
    await fetchData();
  }
  catch {
    notify({
      title: t('assets.custom_price.delete.error.title'),
      message: t('assets.custom_price.delete.error.message', {
        asset: toDeletePrice.name ?? toDeletePrice.id,
      }),
      display: true,
    });
  }
}

function setPriceForm(item: NonFungibleBalance) {
  setOpenDialog(true);
  set(customPrice, {
    fromAsset: item.id,
    toAsset: item.priceAsset,
    price: item.priceInAsset.toFixed(),
  });
}

function showDeleteConfirmation(item: NonFungibleBalance) {
  show(
    {
      title: t('assets.custom_price.delete.tooltip'),
      message: t('assets.custom_price.delete.message', {
        asset: !item ? '' : item.name ?? item.id,
      }),
    },
    () => deletePrice(item),
  );
}

function getAssetPrice(asset: string): BigNumber | undefined {
  return get(assetPrice(asset));
}

watch(ignoredAssetsHandling, () => {
  setPage(1);
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();

  setPostSubmitFunc(fetchData);
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.accounts_balances'), t('non_fungible_balances.title')]">
    <template #buttons>
      <div class="flex flex-row items-center justify-end gap-2">
        <RuiTooltip>
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="loading"
              @click="refreshNonFungibleBalances(true)"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ t('non_fungible_balances.refresh') }}
        </RuiTooltip>
        <ActiveModules :modules="modules" />
        <NftImageRenderingSettingMenu />
      </div>
    </template>

    <RuiCard>
      <NonFungibleBalancesFilter
        class="mb-4"
        :selected="selected"
        :ignored-assets-handling="ignoredAssetsHandling"
        @update:selected="selected = $event"
        @update:ignored-assets-handling="ignoredAssetsHandling = $event"
        @mass-ignore="massIgnore($event)"
      />
      <CollectionHandler
        :collection="balances"
        @set-page="setPage($event)"
      >
        <template #default="{ data, totalUsdValue }">
          <RuiDataTable
            v-model="selected"
            v-model:sort.external="sort"
            v-model:pagination.external="pagination"
            row-attr="id"
            outlined
            dense
            :cols="tableHeaders"
            :rows="data"
            :loading="isLoading"
            show-select
          >
            <template #item.name="{ row }">
              <NftDetails :identifier="row.id" />
            </template>
            <template #item.ignored="{ row }">
              <div class="flex justify-center">
                <RuiSwitch
                  color="primary"
                  hide-details
                  :model-value="isIgnored(row.id).value"
                  @update:model-value="toggleIgnoreAsset(row.id)"
                />
              </div>
            </template>
            <template #item.priceInAsset="{ row }">
              <AmountDisplay
                v-if="row.priceAsset !== currencySymbol"
                :value="row.priceInAsset"
                :asset="row.priceAsset"
              />
              <span v-else>-</span>
            </template>
            <template #item.usdPrice="{ row }">
              <AmountDisplay
                :price-asset="row.priceAsset"
                :amount="row.priceInAsset"
                :value="getAssetPrice(row.priceAsset)"
                no-scramble
                show-currency="symbol"
                :fiat-currency="currencySymbol"
              />
            </template>
            <template #item.actions="{ row }">
              <RowActions
                :delete-tooltip="t('assets.custom_price.delete.tooltip')"
                :edit-tooltip="t('assets.custom_price.edit.tooltip')"
                :delete-disabled="!row.manuallyInput"
                @delete-click="showDeleteConfirmation(row)"
                @edit-click="setPriceForm(row)"
              />
            </template>
            <template #item.manuallyInput="{ row }">
              <SuccessDisplay
                v-if="row.manuallyInput"
                class="mx-auto"
                success
              />
              <div v-else />
            </template>
            <template #body.append>
              <RowAppend
                v-if="totalUsdValue"
                label-colspan="4"
                :label="t('common.total')"
                class="[&>td]:p-4"
                :right-patch-colspan="2"
              >
                <AmountDisplay
                  :value="totalUsdValue"
                  show-currency="symbol"
                  fiat-currency="USD"
                />
              </RowAppend>
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>
    </RuiCard>

    <LatestPriceFormDialog
      :value="customPrice"
      edit-mode
    />
  </TablePageLayout>
</template>

<style scoped lang="scss">
.non-fungible-balances {
  &__item {
    &__preview {
      width: 50px;
      height: 50px;
      max-width: 50px;
    }
  }
}
</style>
