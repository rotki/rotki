<script setup lang="ts">
import type { ActionStatus } from '@/types/action';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { Module } from '@/types/modules';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import type { ManualPriceFormPayload } from '@/types/prices';
import type { DataTableColumn } from '@rotki/ui-library';
import NonFungibleBalancesFilter from '@/components/accounts/balances/NonFungibleBalancesFilter.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import LatestPriceFormDialog from '@/components/price-manager/latest/LatestPriceFormDialog.vue';
import NftImageRenderingSettingMenu from '@/components/settings/general/nft/NftImageRenderingSettingMenu.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { uniqueStrings } from '@/utils/data';

defineProps<{ modules: Module[] }>();

const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNonFungibleBalancesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();
const { notify } = useNotificationsStore();
const { deleteLatestPrice } = useAssetPricesApi();

const openPriceDialog = ref<boolean>(false);
const customPrice = ref<ManualPriceFormPayload | null>(null);

const selected = ref<string[]>([]);
const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');

const extraParams = computed(() => ({
  ignoredAssetsHandling: get(ignoredAssetsHandling),
}));

const tableHeaders = computed<DataTableColumn<NonFungibleBalance>[]>(() => [
  {
    cellClass: 'text-no-wrap',
    key: 'name',
    label: t('common.name'),
    sortable: true,
  },
  {
    align: 'center',
    key: 'ignored',
    label: t('non_fungible_balances.ignore'),
    sortable: false,
  },
  {
    align: 'end',
    class: 'text-no-wrap',
    key: 'priceInAsset',
    label: t('non_fungible_balances.column.price_in_asset'),
    sortable: false,
    width: '75%',
  },
  {
    align: 'end',
    class: 'text-no-wrap',
    key: 'usdPrice',
    label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    sortable: true,
  },
  {
    class: 'text-no-wrap',
    key: 'manuallyInput',
    label: t('non_fungible_balances.column.custom_price'),
    sortable: false,
  },
  {
    align: 'center',
    key: 'actions',
    label: t('common.actions_text'),
    sortable: false,
    width: '50',
  },
]);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

const { setMessage } = useMessageStore();
const { ignoreAsset, ignoreAssetWithConfirmation, isAssetIgnored, unignoreAsset } = useIgnoredAssetsStore();

const {
  fetchData,
  isLoading,
  pagination,
  setPage,
  sort,
  state: balances,
} = usePaginationFilters<
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload
>(fetchNonFungibleBalances, {
  defaultSortBy: [{
    column: 'usdPrice',
    direction: 'desc',
  }],
  extraParams,
  history: 'router',
  onUpdateFilters(query) {
    set(ignoredAssetsHandling, query.ignoredAssetsHandling || 'exclude');
  },
});

const { show } = useConfirmStore();

const isIgnored = (identifier: string) => isAssetIgnored(identifier);

function refreshCallback() {
  if (get(ignoredAssetsHandling) !== 'none') {
    fetchData();
  }
}

async function toggleIgnoreAsset(balance: NonFungibleBalance) {
  const { id, name } = balance;
  if (get(isIgnored(id))) {
    const response = await unignoreAsset(id);
    if (response.success) {
      refreshCallback();
    }
  }
  else {
    await ignoreAssetWithConfirmation(id, name, refreshCallback);
  }
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
      description: t('ignore.no_items.description', choice),
      success: false,
      title: t('ignore.no_items.title', choice),
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
      display: true,
      message: t('assets.custom_price.delete.error.message', {
        asset: toDeletePrice.name ?? toDeletePrice.id,
      }),
      title: t('assets.custom_price.delete.error.title'),
    });
  }
}

function setPriceForm(item: NonFungibleBalance) {
  set(customPrice, {
    fromAsset: item.id,
    price: item.priceInAsset.toFixed(),
    toAsset: item.priceAsset,
  });
  set(openPriceDialog, true);
}

function showDeleteConfirmation(item: NonFungibleBalance) {
  show(
    {
      message: t('assets.custom_price.delete.message', {
        asset: !item ? '' : item.name ?? item.id,
      }),
      title: t('assets.custom_price.delete.tooltip'),
    },
    () => deletePrice(item),
  );
}

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

watch(ignoredAssetsHandling, () => {
  setPage(1);
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.non_fungible_balances')]">
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
                <RuiIcon name="lu-refresh-ccw" />
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
                  @update:model-value="toggleIgnoreAsset(row)"
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
                :value="row.usdPrice"
                no-scramble
                show-currency="symbol"
                fiat-currency="USD"
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
      v-model:open="openPriceDialog"
      :editable-item="customPrice"
      @refresh="fetchData()"
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
