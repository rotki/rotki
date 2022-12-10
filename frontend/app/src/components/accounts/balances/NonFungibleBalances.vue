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
      <active-modules :modules="modules" class="mr-2" />
      <refresh-button
        :loading="loading"
        :tooltip="tc('non_fungible_balances.refresh')"
        @refresh="fetch(true)"
      />
    </template>

    <collection-handler :collection="balances">
      <template #default="{ data, itemLength, totalUsdValue }">
        <data-table
          v-model="selected"
          :headers="tableHeaders"
          :items="data"
          :options="options"
          :server-items-length="itemLength"
          :loading="loading"
          show-select
          multi-sort
          :must-sort="false"
          @update:options="updatePaginationHandler($event)"
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
              show-currency="symbol"
              fiat-currency="USD"
            />
          </template>
          <template #item.actions="{ item }">
            <row-action
              :delete-tooltip="tc('non_fungible_balances.row.delete')"
              :edit-tooltip="tc('non_fungible_balances.row.edit')"
              :delete-disabled="!item.manuallyInput"
              @delete-click="confirmDelete = item"
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
    <confirm-dialog
      :display="!!confirmDelete"
      :title="tc('non_fungible_balances.delete.title')"
      :message="
        tc('non_fungible_balances.delete.message', 0, {
          asset: deleteAsset
        })
      "
      @confirm="deletePrice"
      @cancel="confirmDelete = null"
    />
  </card>
</template>

<script setup lang="ts">
import { dropRight } from 'lodash';
import { type PropType, type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
import NonFungibleBalanceEdit from '@/components/accounts/balances/NonFungibleBalanceEdit.vue';
import NonFungibleBalancesFilter from '@/components/accounts/balances/NonFungibleBalancesFilter.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowAction from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { isSectionLoading } from '@/composables/common';
import { type ManualPriceFormPayload } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type ActionStatus } from '@/store/types';
import { type IgnoredAssetsHandlingType } from '@/types/assets';
import { type Module } from '@/types/modules';
import {
  type NonFungibleBalance,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { Section } from '@/types/status';
import { assert } from '@/utils/assertions';
import { uniqueStrings } from '@/utils/data';

interface PaginationOptions {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof NonFungibleBalance)[];
  sortDesc: boolean[];
}

defineProps({
  modules: {
    required: true,
    type: Array as PropType<Module[]>
  }
});

const balancesStore = useNonFungibleBalancesStore();
const { fetchNonFungibleBalances: fetch, updateRequestPayload } = balancesStore;
const { balances } = storeToRefs(balancesStore);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const options: Ref<PaginationOptions | null> = ref(null);

const { tc } = useI18n();
const { notify } = useNotifications();

const edit: Ref<NonFungibleBalance | null> = ref(null);
const confirmDelete: Ref<NonFungibleBalance | null> = ref(null);

const deleteAsset = computed(() => {
  const balance = get(confirmDelete);
  return !balance ? '' : balance.name ?? balance.id;
});

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
    class: 'text-no-wrap'
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
    await api.assets.addLatestPrice(payload);
    await fetch();
  } catch (e: any) {
    notify({
      title: '',
      message: e.message,
      display: true
    });
  }
};

const deletePrice = async () => {
  const price = get(confirmDelete);
  assert(price);
  set(confirmDelete, null);
  try {
    await api.assets.deleteLatestPrice(price.id);
    await fetch();
  } catch {
    notify({
      title: tc('non_fungible_balances.delete.error.title'),
      message: tc('non_fungible_balances.delete.error.message', 0, {
        asset: price.name ?? price.id
      }),
      display: true
    });
  }
};

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();

const isIgnored = (identifier: string) => {
  return isAssetIgnored(identifier);
};

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
    await fetch();
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
      await fetch();
    }
  }
};

const updatePayloadHandler = async () => {
  let paginationOptions = {};

  const optionsVal = get(options);
  if (optionsVal) {
    const { itemsPerPage, page, sortBy, sortDesc } = optionsVal;
    const offset = (page - 1) * itemsPerPage;

    paginationOptions = {
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy.length > 0 ? sortBy : ['name'],
      ascending:
        sortDesc.length > 1 ? dropRight(sortDesc).map(bool => !bool) : [true]
    };
  }

  const payload: Partial<NonFungibleBalancesRequestPayload> = {
    ignoredAssetsHandling: get(ignoredAssetsHandling),
    ...paginationOptions
  };

  await updateRequestPayload(payload);
};

const updatePaginationHandler = async (
  newOptions: PaginationOptions | null
) => {
  set(options, newOptions);
  await updatePayloadHandler();
};

watch(ignoredAssetsHandling, async (filters, oldValue) => {
  if (filters === oldValue) {
    return;
  }
  let newOptions = null;
  if (get(options)) {
    newOptions = {
      ...get(options)!,
      page: 1
    };
  }

  await updatePaginationHandler(newOptions);
});

onMounted(async () => {
  await updatePayloadHandler();
});
</script>
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

.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>
