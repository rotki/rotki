<script setup lang="ts">
import dropRight from 'lodash/dropRight';
import { type ComputedRef, type PropType, type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
import { type MaybeRef } from '@vueuse/core';
import isEqual from 'lodash/isEqual';
import { type IgnoredAssetsHandlingType } from '@/types/asset';
import { type Module } from '@/types/modules';
import {
  type NonFungibleBalance,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { Section } from '@/types/status';
import { assert } from '@/utils/assertions';
import { uniqueStrings } from '@/utils/data';
import { type TablePagination } from '@/types/pagination';
import { type ActionStatus } from '@/types/action';
import { type ManualPriceFormPayload } from '@/types/prices';
import { defaultCollectionState, defaultOptions } from '@/utils/collection';
import { type Collection } from '@/types/collection';
import {
  type LocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';

defineProps({
  modules: {
    required: true,
    type: Array as PropType<Module[]>
  }
});

const { fetchNonFungibleBalances, refreshNonFungibleBalances } =
  useNonFungibleBalancesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { tc } = useI18n();
const { notify } = useNotificationsStore();
const { addLatestPrice, deleteLatestPrice } = useAssetPricesApi();

const edit: Ref<NonFungibleBalance | null> = ref(null);

const selected: Ref<NonFungibleBalance[]> = ref([]);
const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.name'),
    value: 'name',
    cellClass: 'text-no-wrap'
  },
  {
    text: tc('non_fungible_balances.ignore'),
    value: 'ignored',
    align: 'center',
    sortable: false
  },
  {
    text: tc('non_fungible_balances.column.price_in_asset'),
    value: 'priceInAsset',
    align: 'end',
    width: '75%',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: tc('common.price_in_symbol', 0, { symbol: get(currencySymbol) }),
    value: 'usdPrice',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: tc('non_fungible_balances.column.custom_price'),
    value: 'manuallyInput',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: tc('non_fungible_balances.column.actions'),
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
      title: tc('non_fungible_balances.delete.error.title'),
      message: tc('non_fungible_balances.delete.error.message', 0, {
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
  let success = false;
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
      title: tc('ignore.no_items.title', choice),
      description: tc('ignore.no_items.description', choice)
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

const {
  isLoading,
  state: balances,
  execute
} = useAsyncState<
  Collection<NonFungibleBalance>,
  MaybeRef<NonFungibleBalancesRequestPayload>[]
>(args => fetchNonFungibleBalances(args), defaultCollectionState(), {
  immediate: false,
  resetOnExecute: false,
  delay: 0
});

const fetchData = async (): Promise<void> => {
  await execute(0, pageParams);
};

const options: Ref<TablePagination<NonFungibleBalance>> = ref(
  defaultOptions('name')
);

const pageParams: ComputedRef<NonFungibleBalancesRequestPayload> = computed(
  () => {
    const { itemsPerPage, page, sortBy, sortDesc } = get(options);
    const offset = (page - 1) * itemsPerPage;

    return {
      ignoredAssetsHandling: get(ignoredAssetsHandling),
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy?.length > 0 ? sortBy : ['name'],
      ascending:
        sortDesc && sortDesc.length > 1
          ? dropRight(sortDesc).map(bool => !bool)
          : [true]
    };
  }
);

const router = useRouter();
const route = useRoute();

const applyRouteFilter = () => {
  const query = get(route).query;
  const parsedOptions = RouterPaginationOptionsSchema.parse(query);

  const newIgnoredAssetsHandling = query.ignoredAssetsHandling || 'exclude';

  set(options, {
    ...get(options),
    ...parsedOptions
  });
  set(ignoredAssetsHandling, newIgnoredAssetsHandling);
};

watch(route, () => {
  set(userAction, false);
  applyRouteFilter();
});

onBeforeMount(() => {
  applyRouteFilter();
});

watch(ignoredAssetsHandling, async (filters, oldValue) => {
  if (isEqual(filters, oldValue)) {
    return;
  }

  set(options, { ...get(options), page: 1 });
});

const userAction: Ref<boolean> = ref(false);

const setPage = (page: number) => {
  set(userAction, true);
  set(options, { ...get(options), page });
};

const setOptions = (newOptions: TablePagination<NonFungibleBalance>) => {
  set(userAction, true);
  set(options, newOptions);
};

onMounted(async () => {
  await fetchData();
  await refreshNonFungibleBalances();
});

const getQuery = (): LocationQuery => {
  const opts = get(options);
  assert(opts);
  const { itemsPerPage, page, sortBy, sortDesc } = opts;

  return {
    itemsPerPage: itemsPerPage.toString(),
    page: page.toString(),
    sortBy,
    sortDesc: sortDesc.map(x => x.toString()),
    ignoredAssetsHandling: get(ignoredAssetsHandling)
  };
};

watch(pageParams, async (params, op) => {
  if (isEqual(params, op)) {
    return;
  }
  if (get(userAction)) {
    // Route should only be updated on user action otherwise it messes with
    // forward navigation.
    await router.push({
      query: getQuery()
    });
    set(userAction, false);
  }

  await fetchData();
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
      title: tc('non_fungible_balances.delete.title'),
      message: tc('non_fungible_balances.delete.message', 0, {
        asset: !item ? '' : item.name ?? item.id
      })
    },
    () => deletePrice(item)
  );
};
</script>

<template>
  <card outlined-body>
    <template #title>
      {{ tc('non_fungible_balances.title') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <template #actions>
      <non-fungible-balances-filter
        :selected="selected"
        :ignored-assets-handling="ignoredAssetsHandling"
        @update:selected="selected = $event"
        @update:ignored-assets-handling="ignoredAssetsHandling = $event"
        @mass-ignore="massIgnore"
      />
    </template>
    <template #details>
      <div class="d-flex">
        <nft-image-rendering-setting-menu />
        <active-modules :modules="modules" class="mx-2" />
        <refresh-button
          :loading="loading"
          :tooltip="tc('non_fungible_balances.refresh')"
          @refresh="refreshNonFungibleBalances(true)"
        />
      </div>
    </template>

    <collection-handler :collection="balances" @set-page="setPage">
      <template #default="{ data, itemLength, totalUsdValue }">
        <data-table
          v-model="selected"
          :headers="tableHeaders"
          :items="data"
          :options="options"
          :server-items-length="itemLength"
          :loading="isLoading"
          show-select
          multi-sort
          :must-sort="false"
          @update:options="setOptions($event)"
        >
          <template #item.name="{ item }">
            <nft-details :identifier="item.id" />
          </template>
          <template #item.ignored="{ item }">
            <div class="d-flex justify-center">
              <v-switch
                :input-value="isIgnored(item.id)"
                @change="toggleIgnoreAsset(item.id)"
              />
            </div>
          </template>
          <template #item.priceInAsset="{ item }">
            <amount-display
              v-if="item.priceAsset !== currencySymbol"
              :value="item.priceInAsset"
              :asset="item.priceAsset"
            />
            <span v-else>-</span>
          </template>
          <template #item.usdPrice="{ item }">
            <amount-display
              :price-asset="item.priceAsset"
              :amount="item.priceInAsset"
              :value="item.usdPrice"
              no-scramble
              show-currency="symbol"
              fiat-currency="USD"
            />
          </template>
          <template #item.actions="{ item }">
            <row-actions
              :delete-tooltip="tc('non_fungible_balances.row.delete')"
              :edit-tooltip="tc('non_fungible_balances.row.edit')"
              :delete-disabled="!item.manuallyInput"
              @delete-click="showDeleteConfirmation(item)"
              @edit-click="edit = item"
            />
          </template>
          <template #item.manuallyInput="{ item }">
            <v-icon v-if="item.manuallyInput" color="green">mdi-check</v-icon>
          </template>
          <template #body.append="{ isMobile }">
            <row-append
              label-colspan="4"
              :label="tc('common.total')"
              :right-patch-colspan="1"
              :is-mobile="isMobile"
            >
              <amount-display
                :value="totalUsdValue"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </row-append>
          </template>
        </data-table>
      </template>
    </collection-handler>

    <non-fungible-balance-edit
      v-if="!!edit"
      :value="edit"
      @close="edit = null"
      @save="setPrice($event.price, $event.asset)"
    />
  </card>
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
