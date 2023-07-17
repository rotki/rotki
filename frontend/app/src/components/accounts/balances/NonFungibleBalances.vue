<script setup lang="ts">
import { type PropType, type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type ActionStatus } from '@/types/action';
import { type IgnoredAssetsHandlingType } from '@/types/asset';
import { type Module } from '@/types/modules';
import {
  type NonFungibleBalance,
  type NonFungibleBalanceWithLastPrice,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { type ManualPriceFormPayload } from '@/types/prices';
import { Section } from '@/types/status';

defineProps({
  modules: {
    required: true,
    type: Array as PropType<Module[]>
  }
});

const { fetchNonFungibleBalances, refreshNonFungibleBalances } =
  useNonFungibleBalancesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();
const { notify } = useNotificationsStore();
const { addLatestPrice, deleteLatestPrice } = useAssetPricesApi();

const edit: Ref<NonFungibleBalance | null> = ref(null);

const selected: Ref<NonFungibleBalance[]> = ref([]);
const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');

const extraParams = computed(() => ({
  ignoredAssetsHandling: get(ignoredAssetsHandling)
}));

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.name'),
    value: 'name',
    cellClass: 'text-no-wrap'
  },
  {
    text: t('non_fungible_balances.ignore'),
    value: 'ignored',
    align: 'center',
    sortable: false
  },
  {
    text: t('non_fungible_balances.column.price_in_asset'),
    value: 'priceInAsset',
    align: 'end',
    width: '75%',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    value: 'lastPrice',
    align: 'end',
    class: 'text-no-wrap'
  },
  {
    text: t('non_fungible_balances.column.custom_price'),
    value: 'manuallyInput',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: t('non_fungible_balances.column.actions'),
    value: 'actions',
    align: 'center',
    sortable: false,
    width: '50'
  }
]);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

const setPrice = async (price: string, toAsset: string) => {
  const nft = get(edit);
  set(edit, null);
  assert(nft);
  try {
    const payload: ManualPriceFormPayload = {
      fromAsset: nft.id,
      toAsset,
      price
    };
    await addLatestPrice(payload);
    await fetchData();
  } catch (e: any) {
    notify({
      title: '',
      message: e.message,
      display: true
    });
  }
};

const deletePrice = async (toDeletePrice: NonFungibleBalance) => {
  try {
    await deleteLatestPrice(toDeletePrice.id);
    await fetchData();
  } catch {
    notify({
      title: t('non_fungible_balances.delete.error.title'),
      message: t('non_fungible_balances.delete.error.message', {
        asset: toDeletePrice.name ?? toDeletePrice.id
      }),
      display: true
    });
  }
};

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();

const isIgnored = (identifier: string) => isAssetIgnored(identifier);

const toggleIgnoreAsset = async (identifier: string) => {
  let success;
  if (get(isIgnored(identifier))) {
    const response = await unignoreAsset(identifier);
    success = response.success;
  } else {
    const response = await ignoreAsset(identifier);
    success = response.success;
  }

  if (success && get(ignoredAssetsHandling) !== 'none') {
    await fetchData();
  }
};

const massIgnore = async (ignored: boolean) => {
  const ids = get(selected)
    .filter(item => {
      const isItemIgnored = get(isIgnored(item.id));
      return ignored ? !isItemIgnored : isItemIgnored;
    })
    .map(item => item.id)
    .filter(uniqueStrings);

  let status: ActionStatus;

  if (ids.length === 0) {
    const choice = ignored ? 1 : 2;
    setMessage({
      success: false,
      title: t('ignore.no_items.title', choice),
      description: t('ignore.no_items.description', choice)
    });
    return;
  }

  if (ignored) {
    status = await ignoreAsset(ids);
  } else {
    status = await unignoreAsset(ids);
  }

  if (status.success) {
    set(selected, []);
    if (get(ignoredAssetsHandling) !== 'none') {
      await fetchData();
    }
  }
};

watch(ignoredAssetsHandling, async () => {
  setPage(1);
});

const {
  state: balances,
  isLoading,
  fetchData,
  options,
  setPage,
  setOptions
} = usePaginationFilters<
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload,
  NonFungibleBalanceWithLastPrice
>(null, true, useEmptyFilter, fetchNonFungibleBalances, {
  onUpdateFilters(query) {
    set(ignoredAssetsHandling, query.ignoredAssetsHandling || 'exclude');
  },
  extraParams,
  defaultSortBy: {
    key: 'lastPrice',
    ascending: [false]
  }
});

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: NonFungibleBalance) => {
  show(
    {
      title: t('non_fungible_balances.delete.title'),
      message: t('non_fungible_balances.delete.message', {
        asset: !item ? '' : item.name ?? item.id
      })
    },
    () => deletePrice(item)
  );
};
</script>

<template>
  <Card outlined-body>
    <template #title>
      {{ t('non_fungible_balances.title') }}
      <VIcon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </VIcon>
    </template>
    <template #actions>
      <NonFungibleBalancesFilter
        :selected="selected"
        :ignored-assets-handling="ignoredAssetsHandling"
        @update:selected="selected = $event"
        @update:ignored-assets-handling="ignoredAssetsHandling = $event"
        @mass-ignore="massIgnore($event)"
      />
    </template>
    <template #details>
      <div class="d-flex">
        <NftImageRenderingSettingMenu />
        <ActiveModules :modules="modules" class="mx-2" />
        <RefreshButton
          :loading="loading"
          :tooltip="t('non_fungible_balances.refresh')"
          @refresh="refreshNonFungibleBalances(true)"
        />
      </div>
    </template>

    <CollectionHandler :collection="balances" @set-page="setPage($event)">
      <template #default="{ data, itemLength, totalUsdValue }">
        <DataTable
          v-model="selected"
          :headers="tableHeaders"
          :items="data"
          :options="options"
          :server-items-length="itemLength"
          :loading="isLoading"
          show-select
          @update:options="setOptions($event)"
        >
          <template #item.name="{ item }">
            <NftDetails :identifier="item.id" />
          </template>
          <template #item.ignored="{ item }">
            <div class="d-flex justify-center">
              <VSwitch
                :input-value="isIgnored(item.id)"
                @change="toggleIgnoreAsset(item.id)"
              />
            </div>
          </template>
          <template #item.priceInAsset="{ item }">
            <AmountDisplay
              v-if="item.priceAsset !== currencySymbol"
              :value="item.priceInAsset"
              :asset="item.priceAsset"
            />
            <span v-else>-</span>
          </template>
          <template #item.lastPrice="{ item }">
            <AmountDisplay
              :price-asset="item.priceAsset"
              :amount="item.priceInAsset"
              :value="item.usdPrice"
              no-scramble
              show-currency="symbol"
              fiat-currency="USD"
            />
          </template>
          <template #item.actions="{ item }">
            <RowActions
              :delete-tooltip="t('non_fungible_balances.row.delete')"
              :edit-tooltip="t('non_fungible_balances.row.edit')"
              :delete-disabled="!item.manuallyInput"
              @delete-click="showDeleteConfirmation(item)"
              @edit-click="edit = item"
            />
          </template>
          <template #item.manuallyInput="{ item }">
            <VIcon v-if="item.manuallyInput" color="green">mdi-check</VIcon>
          </template>
          <template #body.append="{ isMobile }">
            <RowAppend
              label-colspan="4"
              :label="t('common.total')"
              :right-patch-colspan="1"
              :is-mobile="isMobile"
            >
              <AmountDisplay
                :value="totalUsdValue"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </RowAppend>
          </template>
        </DataTable>
      </template>
    </CollectionHandler>

    <NonFungibleBalanceEdit
      v-if="!!edit"
      :value="edit"
      @close="edit = null"
      @save="setPrice($event.price, $event.asset)"
    />
  </Card>
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
