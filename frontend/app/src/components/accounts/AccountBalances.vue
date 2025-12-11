<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/types/blockchain/accounts';
import type { LocationQuery } from '@/types/route';
import { toSentenceCase } from '@rotki/common';
import AccountAssetSelectionActions from '@/components/accounts/AccountAssetSelectionActions.vue';
import AccountBalanceAggregatedAssets from '@/components/accounts/AccountBalanceAggregatedAssets.vue';
import AccountGroupDetails from '@/components/accounts/AccountGroupDetails.vue';
import AccountGroupDetailsTable from '@/components/accounts/AccountGroupDetailsTable.vue';
import AccountBalanceDetails from '@/components/accounts/balances/AccountBalanceDetails.vue';
import DetectEvmAccounts from '@/components/accounts/balances/DetectEvmAccounts.vue';
import DetectTokenChainsSelection from '@/components/accounts/balances/DetectTokenChainsSelection.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { useAccountAssetSelection } from '@/composables/accounts/use-account-asset-selection';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { useRefresh } from '@/composables/balances/refresh';
import { useBlockchains } from '@/composables/blockchain';
import { AccountExternalFilterSchema, type Filters, type Matcher, useBlockchainAccountFilter } from '@/composables/filters/blockchain-account';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { AccountBalancesTable } from '@/modules/accounts/table';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useConfirmStore } from '@/store/confirm';
import { SavedFilterLocation } from '@/types/filtering';
import { getAccountAddress, getGroupId } from '@/utils/blockchain/accounts/utils';
import { fromUriEncoded, toUriEncoded } from '@/utils/route-uri';

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
const accountTable = ref<ComponentExposed<typeof AccountBalancesTable>>();
const detailsTable = ref<ComponentExposed<typeof AccountGroupDetailsTable>>();
const tab = ref<number>(0);
const expanded = ref<string[]>([]);
const query = ref<LocationQuery>({});

const { fetchAccounts: fetchAccountsPage } = useBlockchainAccountData();
const { handleBlockchainRefresh, refreshBlockchainBalances } = useRefresh();
const { fetchAccounts } = useBlockchains();

const { balances } = storeToRefs(useBalancesStore());
const { accounts: accountsState } = storeToRefs(useBlockchainAccountsStore());

const {
  fetchData,
  filters,
  matchers,
  pagination,
  sort,
  state: accounts,
} = usePaginationFilters<
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  Filters,
  Matcher
>(fetchAccountsPage, {
  defaultSortBy: {
    column: 'usdValue',
    direction: 'desc',
  },
  extraParams: computed(() => ({
    category: get(category),
    tags: get(visibleTags),
  })),
  filterSchema: () => useBlockchainAccountFilter(t, category),
  history: 'router',
  onUpdateFilters(filterQuery) {
    const { expanded: expandedIds, q, tab: qTab, tags } = AccountExternalFilterSchema.parse(filterQuery);
    if (tags)
      set(visibleTags, tags);
    if (qTab !== undefined)
      set(tab, qTab);
    if (expandedIds)
      set(expanded, expandedIds);

    set(query, q ? fromUriEncoded(q) : {});
  },
  queryParamsOnly: computed(() => ({
    ...(get(expanded).length > 0
      ? {
          expanded: get(expanded),
          tab: get(tab),
          ...(get(tab) === 1
            ? {
                q: toUriEncoded(get(query)),
              }
            : {}),
        }
      : {}),
  })),
  requestParams: computed(() => ({
    excluded: get(chainExclusionFilter),
  })),
});

const { isDetectingTokens, isSectionLoading, operationRunning, refreshDisabled } = useBlockchainAccountLoading(category);

const { chainIds, isEvm } = useAccountCategoryHelper(category);

const isSolana = computed<boolean>(() => get(category) === 'solana');
const showSelectionToggle = computed<boolean>(() => get(isEvm) || get(isSolana));

async function refreshClick() {
  const chains = get(chainIds);
  await fetchAccounts(chains, true);
  if (get(isEvm))
    await handleBlockchainRefresh(chains);
  else
    await refreshBlockchainBalances(chains);
  await fetchData();
}

function getChains(row: BlockchainAccountGroupWithBalance): string[] {
  const chains = row.chains;
  const excludedChains = get(chainExclusionFilter)[getGroupId(row)];
  return excludedChains ? chains.filter(chain => !excludedChains.includes(chain)) : chains;
}

const { show } = useConfirmStore();

function redetectAllClicked() {
  show({
    message: t('account_balances.detect_tokens.confirmation.message'),
    title: t('account_balances.detect_tokens.confirmation.title'),
    type: 'info',
  }, () => {
    handleBlockchainRefresh(undefined, true);
  });
}

watchDebounced(
  logicOr(isDetectingTokens, isSectionLoading, operationRunning),
  async (isLoading, wasLoading) => {
    if (!isLoading && wasLoading)
      await fetchData();
  },
  {
    debounce: 800,
  },
);

watchImmediate([accountsState, balances], () => {
  fetchData();
});

// Selection mode for bulk asset operations
const {
  handleIgnoreSelected,
  handleMarkSelectedAsSpam,
  selectedAssets,
  selectionMode,
  toggleSelectionMode,
} = useAccountAssetSelection(fetchData);

defineExpose({
  refresh: async () => {
    await fetchData();
    if (!isDefined(detailsTable))
      return;

    await get(detailsTable).refresh();
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
        :disabled="accounts.data.length === 0"
        @clear-selection="selectedAssets = []"
        @ignore="handleIgnoreSelected($event)"
        @mark-spam="handleMarkSelectedAsSpam()"
        @toggle-mode="toggleSelectionMode()"
      />

      <template v-if="!showSelectionToggle || !selectionMode">
        <div
          class="flex items-center gap-2 flex-1"
          :class="{ 'hidden lg:block': !isEvm }"
        >
          <template v-if="isEvm">
            <RuiButtonGroup
              variant="outlined"
              color="primary"
            >
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
              >
                <template #activator>
                  <RuiButton
                    class="py-2 !outline-0 rounded-none"
                    variant="outlined"
                    color="primary"
                    :loading="isDetectingTokens"
                    :disabled="refreshDisabled"
                    @click="redetectAllClicked()"
                  >
                    <template #prepend>
                      <RuiIcon name="lu-refresh-ccw" />
                    </template>

                    {{ t('account_balances.detect_tokens.tooltip.redetect') }}
                  </RuiButton>
                </template>
                {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
              </RuiTooltip>

              <DetectTokenChainsSelection @redetect:all="redetectAllClicked()" />
            </RuiButtonGroup>

            <DetectEvmAccounts />
          </template>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <TagFilter
            v-model="visibleTags"
            class="w-[20rem] max-w-[30rem]"
            hide-details
          />
          <TableFilter
            v-model:matches="filters"
            :matchers="matchers"
            class="max-w-[calc(100vw-11rem)] w-[25rem] lg:max-w-[30rem]"
            :location="SavedFilterLocation.BLOCKCHAIN_ACCOUNTS"
          />
        </div>
      </template>
    </div>

    <AccountBalancesTable
      ref="accountTable"
      v-model:pagination="pagination"
      v-model:sort="sort"
      v-model:chain-filter="chainExclusionFilter"
      v-model:expanded-ids="expanded"
      :data-category="category"
      :category="category"
      class="mt-4"
      :class="[
        { '[&_button[class*=_expander_]]:!animate-pulse-highlight': (expanded.length === 0 && selectionMode) },
      ]"
      group="evm"
      :accounts="accounts"
      @edit="emit('edit', $event)"
      @refresh="fetchData()"
    >
      <template #details="{ row }">
        <AccountGroupDetails
          v-if="row.expansion === 'accounts'"
          v-model="tab"
          :is-xpub="row.data.type === 'xpub'"
        >
          <template #per-chain>
            <AccountGroupDetailsTable
              v-if="row.expansion === 'accounts'"
              ref="detailsTable"
              v-model:query="query"
              v-model:selected="selectedAssets"
              :chains="getChains(row)"
              :tags="visibleTags"
              :group-id="getGroupId(row)"
              :group="row.data.type === 'xpub' ? 'xpub' : undefined"
              :category="row.category || ''"
              :selection-mode="selectionMode"
              @edit="emit('edit', $event)"
            />
          </template>
          <template #aggregated>
            <AccountBalanceAggregatedAssets
              v-model:selected="selectedAssets"
              :group-id="getGroupId(row)"
              :chains="getChains(row)"
              :selection-mode="selectionMode"
            />
          </template>
        </AccountGroupDetails>
        <AccountBalanceDetails
          v-else-if="row.expansion === 'assets'"
          v-model:selected="selectedAssets"
          :address="getAccountAddress(row)"
          :chain="row.chains[0]"
          :selection-mode="selectionMode"
        />
      </template>
    </AccountBalancesTable>
  </RuiCard>
</template>
