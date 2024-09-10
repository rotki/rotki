<script setup lang="ts">
import { SavedFilterLocation } from '@/types/filtering';
import { AccountExternalFilterSchema, type Filters, type Matcher } from '@/composables/filters/blockchain-account';
import AccountBalancesTable from '@/components/accounts/AccountBalancesTable.vue';
import AccountGroupDetails from '@/components/accounts/AccountGroupDetails.vue';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type { Collection } from '@/types/collection';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/types/blockchain/accounts';
import type { ComponentExposed } from 'vue-component-type-helpers';

const props = defineProps<{
  category: string;
}>();

const emit = defineEmits<{
  (e: 'edit', account: AccountManageState): void;
}>();

const { category } = toRefs(props);
const { t } = useI18n();

const visibleTags = ref<string[]>([]);
const chainExclusionFilter = ref<Record<string, string[]>>({});
const accountTable = ref<ComponentExposed<typeof AccountBalancesTable>>();
const detailsTable = ref<ComponentExposed<typeof AccountGroupDetails>>();
const tab = ref<number>(0);

const blockchainStore = useBlockchainStore();
const { fetchAccounts: fetchAccountsPage } = blockchainStore;
const { groups } = storeToRefs(blockchainStore);
const { handleBlockchainRefresh } = useRefresh();
const { fetchAccounts } = useBlockchains();

const {
  filters,
  matchers,
  state: accounts,
  fetchData,
  pagination,
  sort,
} = usePaginationFilters<
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountGroupWithBalance,
  Collection<BlockchainAccountGroupWithBalance>,
  Filters,
  Matcher
>(
  null,
  true,
  () => useBlockchainAccountFilter(t, category),
  fetchAccountsPage,
  {
    extraParams: computed(() => ({
      tags: get(visibleTags),
      ...(get(category) !== 'all' ? { category: get(category) } : {}),
    })),
    onUpdateFilters(query) {
      const externalFilterSchema = AccountExternalFilterSchema.parse(query);
      if (externalFilterSchema.tags)
        set(visibleTags, externalFilterSchema.tags);
    },
    customPageParams: computed(() => ({
      excluded: get(chainExclusionFilter),
    })),
    defaultSortBy: {
      key: 'usdValue',
    },
  },
);

const isEvm = computed(() => get(category) === 'evm');
const showEvmElements = computed(() => get(isEvm) || get(category) === 'all');

const { refreshDisabled, isDetectingTokens } = useBlockchainAccountLoading(fetchData);

async function refreshClick() {
  await fetchAccounts(undefined, true);
  await handleBlockchainRefresh();
  await fetchData();
}

function getChains(row: BlockchainAccountGroupWithBalance): string[] {
  const chains = row.chains;
  const excludedChains = get(chainExclusionFilter)[getGroupId(row)];
  return excludedChains ? chains.filter(chain => !excludedChains.includes(chain)) : chains;
}

watchImmediate(groups, async () => {
  await fetchData();
});

defineExpose({
  refresh: async () => {
    await fetchData();
    if (!isDefined(detailsTable))
      return;

    await get(detailsTable).refresh();
  },
});
</script>

<template>
  <RuiCard data-cy="account-balances">
    <template #header>
      <div class="flex flex-row items-center gap-2">
        <SummaryCardRefreshMenu
          data-cy="account-balances-refresh-menu"
          :disabled="refreshDisabled"
          :loading="isDetectingTokens"
          :tooltip="t('account_balances.refresh_tooltip')"
          @refresh="refreshClick()"
        >
          <template
            v-if="showEvmElements"
            #refreshMenu
          >
            <BlockchainBalanceRefreshBehaviourMenu />
          </template>
        </SummaryCardRefreshMenu>
        <CardTitle class="ml-2">
          {{ t('account_balances.data_table.group', { type: isEvm ? 'EVM' : toSentenceCase(category) }) }}
        </CardTitle>
      </div>
    </template>

    <div class="flex flex-col md:flex-row md:items-center gap-4 flex-wrap">
      <div
        class="flex items-center gap-2 flex-1"
        :class="{ 'hidden lg:block': !(showEvmElements) }"
      >
        <template v-if="showEvmElements">
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                class="py-2"
                variant="outlined"
                color="primary"
                :loading="isDetectingTokens"
                :disabled="refreshDisabled"
                @click="handleBlockchainRefresh(undefined, true)"
              >
                <template #prepend>
                  <RuiIcon name="refresh-line" />
                </template>

                {{ t('account_balances.detect_tokens.tooltip.redetect') }}
              </RuiButton>
            </template>
            {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
          </RuiTooltip>

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
    </div>

    <AccountBalancesTable
      ref="accountTable"
      v-model:pagination="pagination"
      v-model:sort="sort"
      v-model:chain-filter="chainExclusionFilter"
      :data-category="category"
      class="mt-4"
      group
      :accounts="accounts"
      :show-group-label="category === 'all'"
      @edit="emit('edit', $event)"
      @refresh="fetchData()"
    >
      <template #details="{ row }">
        <AccountGroupDetails
          v-if="row.expansion === 'accounts'"
          ref="detailsTable"
          v-model.tab="tab"
          :chains="getChains(row)"
          :tags="visibleTags"
          :group-id="getGroupId(row)"
          :is-xpub="row.data.type === 'xpub'"
          :is-evm="row.category === 'evm'"
          @edit="emit('edit', $event)"
        />
        <AccountBalanceDetails
          v-else-if="row.expansion === 'assets'"
          :address="getAccountAddress(row)"
          :chain="row.chains[0]"
        />
      </template>
    </AccountBalancesTable>
  </ruicard>
</template>
