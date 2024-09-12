<script setup lang="ts">
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type {
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

const props = defineProps<{
  groupId: string;
  chains: string[];
  tags?: string[];
  isXpub: boolean;
  isEvm: boolean;
}>();

const emit = defineEmits<{
  (e: 'edit', account: AccountManageState): void;
}>();

const tab = defineModel<number>({ required: true });

const { fetchGroupAccounts } = useBlockchainStore();

const {
  state: accounts,
  fetchData,
  pagination,
  sort,
} = usePaginationFilters<BlockchainAccountWithBalance, BlockchainAccountGroupRequestPayload>(
  null,
  false,
  useEmptyFilter,
  fetchGroupAccounts,
  {
    extraParams: computed(() => ({
      groupId: props.groupId,
      chain: props.chains,
      tags: props.tags,
    })),
    defaultSortBy: {
      key: 'usdValue',
    },
  },
);

useBlockchainAccountLoading(fetchData);

onMounted(() => {
  nextTick(() => fetchData());
});

defineExpose({
  refresh: fetchData,
});

const { t } = useI18n();

const [DefineAccounts, ReuseAccounts] = createReusableTemplate();
</script>

<template>
  <DefineAccounts>
    <AccountBalancesTable
      v-model:pagination="pagination"
      v-model:sort="sort"
      class="bg-white dark:bg-[#1E1E1E]"
      :accounts="accounts"
      :is-evm="isEvm"
      @edit="emit('edit', $event)"
      @refresh="fetchData()"
    >
      <template #details="{ row }">
        <AccountBalanceDetails
          :address="getAccountAddress(row)"
          :chain="row.chain"
        />
      </template>
    </AccountBalancesTable>
  </DefineAccounts>
  <ReuseAccounts
    v-if="isXpub"
    class="my-2"
  />
  <div
    v-else
    class="rounded-xl my-2"
  >
    <RuiTabs
      v-model="tab"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-3"
    >
      <RuiTab>{{ t('account_balances.aggregated_assets') }}</RuiTab>
      <RuiTab>{{ t('account_balances.per_chain') }}</RuiTab>
    </RuiTabs>
    <RuiTabItems :model-value="tab">
      <RuiTabItem>
        <AccountBalanceAggregatedAssets
          :group-id="groupId"
          :chains="chains"
        />
      </RuiTabItem>
      <RuiTabItem>
        <ReuseAccounts />
      </RuiTabItem>
    </RuiTabItems>
  </div>
</template>
