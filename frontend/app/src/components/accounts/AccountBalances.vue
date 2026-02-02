<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type { BlockchainAccountGroupWithBalance } from '@/types/blockchain/accounts';
import type { LocationQuery } from '@/types/route';
import { toSentenceCase } from '@rotki/common';
import AccountAssetSelectionActions from '@/components/accounts/AccountAssetSelectionActions.vue';
import AccountBalancesFilterBar from '@/components/accounts/AccountBalancesFilterBar.vue';
import AccountExpandedRowContent from '@/components/accounts/AccountExpandedRowContent.vue';
import AccountTokenDetectionControls from '@/components/accounts/AccountTokenDetectionControls.vue';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { useAccountAssetSelection } from '@/composables/accounts/use-account-asset-selection';
import { useAccountBalancesPagination } from '@/composables/accounts/use-account-balances-pagination';
import { useAccountBalancesRefresh } from '@/composables/accounts/use-account-balances-refresh';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { AccountBalancesTable } from '@/modules/accounts/table';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { getGroupId } from '@/utils/blockchain/accounts/utils';

const props = defineProps<{
  category: string;
}>();

const emit = defineEmits<{
  edit: [account: AccountManageState];
}>();

const { category } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });

const visibleTags = ref<string[]>([]);
const chainExclusionFilter = ref<Record<string, string[]>>({});
const expandedRowContent = ref<ComponentExposed<typeof AccountExpandedRowContent>>();
const tab = ref<number>(0);
const expanded = ref<string[]>([]);
const query = ref<LocationQuery>({});

const { balances } = storeToRefs(useBalancesStore());
const { accounts: accountsState } = storeToRefs(useBlockchainAccountsStore());

const {
  accounts,
  fetchData,
  filters,
  matchers,
  pagination,
  sort,
} = useAccountBalancesPagination({
  category,
  chainExclusionFilter,
  expanded,
  query,
  tab,
  visibleTags,
});

const { isLoadingActive, isDetectingTokens, refreshDisabled } = useBlockchainAccountLoading(category);

const { chainIds, isEvm } = useAccountCategoryHelper(category);

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

// Computed
const isSolana = computed<boolean>(() => get(category) === 'solana');
const showSelectionToggle = computed<boolean>(() => get(isEvm) || get(isSolana));

const anyExpansion = computed<boolean>(() => get(accounts).data.some(item => item.expansion));

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
  <RuiCard data-cy="account-balances">
    <template #header>
      {{ t('account_balances.data_table.group', { type: isEvm ? 'EVM' : toSentenceCase(category) }) }}
    </template>

    <div class="flex flex-col md:flex-row md:items-center gap-4 flex-wrap">
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

      <template v-if="!showSelectionToggle || !selectionMode">
        <AccountTokenDetectionControls
          v-if="isEvm"
          :is-detecting-tokens="isDetectingTokens"
          :refresh-disabled="refreshDisabled"
        />
        <div
          v-else
          class="flex-1 hidden lg:block"
        />

        <AccountBalancesFilterBar
          v-model:visible-tags="visibleTags"
          v-model:filters="filters"
          :matchers="matchers"
        />
      </template>
    </div>

    <AccountBalancesTable
      v-model:pagination="pagination"
      v-model:sort="sort"
      v-model:chain-filter="chainExclusionFilter"
      v-model:expanded-ids="expanded"
      :data-category="category"
      :category="category"
      class="mt-4"
      :class="{ '[&_button[class*=_expander_]]:!animate-pulse-highlight': expanded.length === 0 && selectionMode }"
      group="evm"
      :accounts="accounts"
      @edit="emit('edit', $event)"
      @refresh="fetchData()"
    >
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
  </RuiCard>
</template>
