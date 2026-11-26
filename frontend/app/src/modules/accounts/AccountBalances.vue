<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { startPromise } from '@shared/utils';
import { createReusableTemplate, isDefined } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, ref, useTemplateRef } from 'vue';
import { getGroupId } from '@/modules/accounts/account-utils';
import AccountAssetSelectionActions from '@/modules/accounts/AccountAssetSelectionActions.vue';
import AccountBalancesEmptyNotice from '@/modules/accounts/AccountBalancesEmptyNotice.vue';
import AccountBalancesFilterBar from '@/modules/accounts/AccountBalancesFilterBar.vue';
import AccountDetailsDrawer from '@/modules/accounts/details/AccountDetailsDrawer.vue';
import AccountBalancesTable from '@/modules/accounts/table/AccountBalancesTable.vue';
import { useAccountAssetSelection } from '@/modules/accounts/use-account-asset-selection';
import { useAccountBalancesFetchTriggers } from '@/modules/accounts/use-account-balances-fetch-triggers';
import { useAccountBalancesPagination } from '@/modules/accounts/use-account-balances-pagination';
import { useAccountBalancesRefresh } from '@/modules/accounts/use-account-balances-refresh';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import TableFrame from '@/modules/core/table/TableFrame.vue';

const { category } = defineProps<{
  category: string;
}>();

const emit = defineEmits<{
  edit: [account: AccountManageState];
  add: [];
}>();

const visibleTags = ref<string[]>([]);
const addresses = ref<string[]>([]);
const chains = ref<string[]>([]);
const chainExclusionFilter = ref<Record<string, string[]>>({});
const detailsDrawer = useTemplateRef<ComponentExposed<typeof AccountDetailsDrawer>>('detailsDrawer');

const {
  accounts,
  fetchData,
  isLoading: isFetching,
  pagination,
  sort,
} = useAccountBalancesPagination({
  addresses,
  chains,
  category: () => category,
  chainExclusionFilter,
  visibleTags,
});

const { chainIds, isEvm } = useAccountCategoryHelper(() => category);

const { refreshClick } = useAccountBalancesRefresh({
  chainIds,
  fetchData,
  isEvm,
});

const {
  handleIgnoreSelected,
  handleMarkSelectedAsSpam,
  selectedAssets,
  selectionMode,
  toggleSelectionMode,
} = useAccountAssetSelection(fetchData);

/** The selection bar, drawn on the page and again inside the details drawer while it is in use. */
const [DefineSelectionActions, ReuseSelectionActions] = createReusableTemplate();

const isSolana = computed<boolean>(() => category === 'solana');
const showSelectionToggle = computed<boolean>(() => get(isEvm) || get(isSolana));

const anyExpansion = computed<boolean>(() => get(accounts).data.some(item => item.expansion));

const filtered = computed<boolean>(() => get(visibleTags).length > 0 || get(addresses).length > 0 || get(chains).length > 0);

function clearFilters(): void {
  set(visibleTags, []);
  set(addresses, []);
  set(chains, []);
}

function openDetails(row: BlockchainAccountGroupWithBalance): void {
  if (isDefined(detailsDrawer))
    startPromise(get(detailsDrawer).open(getGroupId(row)));
}

const { awaitingAccounts } = useAccountBalancesFetchTriggers({
  accounts,
  category: () => category,
  chainIds,
  fetchData,
  isFetching,
});

defineExpose({
  refresh: async () => {
    await fetchData();
    if (!isDefined(detailsDrawer))
      return;

    await get(detailsDrawer).refresh();
  },
  refreshClick,
});
</script>

<template>
  <DefineSelectionActions>
    <AccountAssetSelectionActions
      :selected-count="selectedAssets?.length"
      :selection-mode="selectionMode"
      :show-selection-toggle="showSelectionToggle"
      :disabled="accounts.data.length === 0 || !anyExpansion"
      @clear-selection="selectedAssets = []"
      @ignore="handleIgnoreSelected($event)"
      @mark-spam="handleMarkSelectedAsSpam()"
      @toggle-mode="toggleSelectionMode()"
    />
  </DefineSelectionActions>
  <TableFrame data-testid="account-balances">
    <template #toolbar>
      <ReuseSelectionActions />

      <template v-if="!showSelectionToggle || !selectionMode">
        <AccountBalancesFilterBar
          v-model:visible-tags="visibleTags"
          v-model:addresses="addresses"
          v-model:chains="chains"
          :category="category"
        />
      </template>
    </template>

    <AccountBalancesTable
      v-model:pagination="pagination"
      v-model:sort="sort"
      v-model:chain-filter="chainExclusionFilter"
      :data-category="category"
      :category="category"
      framed
      details-in-drawer
      row-refresh
      :class="{ '[&_[data-id=expand-button]]:animate-pulse-highlight!': selectionMode && !detailsDrawer?.isOpen }"
      group="evm"
      :accounts="accounts"
      :fetching="awaitingAccounts"
      @edit="emit('edit', $event)"
      @refresh="fetchData()"
      @refresh-chains="startPromise(refreshClick($event))"
      @open-details="openDetails($event)"
    >
      <template #empty>
        <AccountBalancesEmptyNotice
          :filtered="filtered"
          @clear-filters="clearFilters()"
          @add="emit('add')"
        />
      </template>
    </AccountBalancesTable>
    <AccountDetailsDrawer
      ref="detailsDrawer"
      v-model:selected-assets="selectedAssets"
      v-model:chain-exclusion-filter="chainExclusionFilter"
      :category="category"
      :visible-tags="visibleTags"
      :selection-mode="selectionMode"
      @edit="emit('edit', $event)"
    >
      <template #selection-actions>
        <ReuseSelectionActions />
      </template>
    </AccountDetailsDrawer>
  </TableFrame>
</template>
