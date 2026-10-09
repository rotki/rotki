<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import type { LocationQuery } from '@/modules/core/table/route';
import { getGroupId } from '@/modules/accounts/account-utils';
import AccountAssetSelectionActions from '@/modules/accounts/AccountAssetSelectionActions.vue';
import AccountBalancesFilterBar from '@/modules/accounts/AccountBalancesFilterBar.vue';
import AccountExpandedRowContent from '@/modules/accounts/AccountExpandedRowContent.vue';
import AccountBalancesTable from '@/modules/accounts/table/AccountBalancesTable.vue';
import { useAccountAssetSelection } from '@/modules/accounts/use-account-asset-selection';
import { useAccountBalancesPagination } from '@/modules/accounts/use-account-balances-pagination';
import { useAccountBalancesRefresh } from '@/modules/accounts/use-account-balances-refresh';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';

const { category } = defineProps<{
  category: string;
}>();

const emit = defineEmits<{
  edit: [account: AccountManageState];
  add: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const visibleTags = ref<string[]>([]);
const addresses = ref<string[]>([]);
const chains = ref<string[]>([]);
const chainExclusionFilter = ref<Record<string, string[]>>({});
const expandedRowContent = useTemplateRef<ComponentExposed<typeof AccountExpandedRowContent>>('expandedRowContent');
const tab = ref<number>(0);
const expanded = ref<string[]>([]);
const query = ref<LocationQuery>({});

const { balances } = storeToRefs(useBalancesStore());
const accountsStore = useBlockchainAccountsStore();
const { accounts: accountsState } = storeToRefs(accountsStore);
const { isChainSettled } = accountsStore;

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
  expanded,
  query,
  tab,
  visibleTags,
});

const { isLoadingActive } = useBlockchainAccountLoading(() => category);

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

const isSolana = computed<boolean>(() => category === 'solana');
const showSelectionToggle = computed<boolean>(() => get(isEvm) || get(isSolana));

const anyExpansion = computed<boolean>(() => get(accounts).data.some(item => item.expansion));

const filtered = computed<boolean>(() => get(visibleTags).length > 0 || get(addresses).length > 0 || get(chains).length > 0);

/**
 * Whether an empty page is not the answer yet, so the table shows loading rather than "no accounts".
 *
 * @remarks
 * Until a chain of the category has settled (its accounts read loaded or failed), nothing is known,
 * and the page fetch that runs before the accounts land comes back empty. A failed read settles
 * the chain too, so the table then shows the empty state or the fetch error instead of spinning.
 */
const awaitingAccounts = computed<boolean>(() => {
  if (get(accounts).data.length > 0)
    return false;
  // with no chains known for the category there is nothing to wait on
  const categoryChains = get(chainIds);
  return get(isFetching) || (categoryChains.length > 0 && !categoryChains.some(chain => isChainSettled(chain)));
});

/** An empty table says whether the filters hid every account or there are none yet, and offers the way out. */
const emptyNotice = computed<{ icon: RuiIcons; title: string; description: string }>(() => get(filtered)
  ? {
      description: t('account_balances.empty.filtered_description'),
      icon: 'lu-search-x',
      title: t('account_balances.empty.filtered_title'),
    }
  : {
      description: t('account_balances.empty.description'),
      icon: 'lu-wallet-minimal',
      title: t('account_balances.empty.title'),
    });

function clearFilters(): void {
  set(visibleTags, []);
  set(addresses, []);
  set(chains, []);
}

function getChains(row: BlockchainAccountGroupWithBalance): string[] {
  const chains = row.chains;
  const excludedChains = get(chainExclusionFilter)[getGroupId(row)];
  return excludedChains ? chains.filter(chain => !excludedChains.includes(chain)) : chains;
}

watchDebounced(isLoadingActive, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
}, { debounce: 800 });

watchImmediate([accountsState, balances], () => {
  fetchData();
});

defineExpose({
  refresh: async () => {
    await fetchData();
    if (!isDefined(expandedRowContent))
      return;

    await get(expandedRowContent).refresh();
  },
  refreshClick,
});
</script>

<template>
  <TableFrame data-testid="account-balances">
    <template #toolbar>
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

      <!-- token and account detection live in the page's Refresh menu, so the bar holds selection and filters -->
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
      v-model:expanded-ids="expanded"
      :data-category="category"
      :category="category"
      framed
      :class="{ '[&_[data-id=expand-button]]:animate-pulse-highlight!': expanded.length === 0 && selectionMode }"
      group="evm"
      :accounts="accounts"
      :fetching="awaitingAccounts"
      @edit="emit('edit', $event)"
      @refresh="fetchData()"
    >
      <template #empty>
        <TableEmptyNotice
          :icon="emptyNotice.icon"
          :title="emptyNotice.title"
          :description="emptyNotice.description"
        >
          <RuiButton
            v-if="filtered"
            variant="outlined"
            color="primary"
            data-testid="accounts-empty-clear-filters"
            @click="clearFilters()"
          >
            {{ t('account_balances.empty.clear_filters') }}
          </RuiButton>
          <RuiButton
            v-else
            color="primary"
            data-testid="accounts-empty-add"
            @click="emit('add')"
          >
            <template #prepend>
              <RuiIcon name="lu-plus" />
            </template>
            {{ t('blockchain_balances.add_account') }}
          </RuiButton>
        </TableEmptyNotice>
      </template>
      <template #details="{ row }">
        <AccountExpandedRowContent
          ref="expandedRowContent"
          v-model:tab="tab"
          v-model:query="query"
          v-model:selected-assets="selectedAssets"
          :row="row"
          :visible-tags="visibleTags"
          :chains="getChains(row)"
          :selection-mode="selectionMode"
          @edit="emit('edit', $event)"
        />
      </template>
    </AccountBalancesTable>
  </TableFrame>
</template>
