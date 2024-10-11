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
  isEvm: boolean;
}>();

const emit = defineEmits<{
  (e: 'edit', account: AccountManageState): void;
}>();

const { fetchGroupAccounts } = useBlockchainStore();

const {
  state: accounts,
  fetchData,
  pagination,
  sort,
} = usePaginationFilters<BlockchainAccountWithBalance, BlockchainAccountGroupRequestPayload>(fetchGroupAccounts, {
  customPageParams: computed(() => ({
    groupId: props.groupId,
    chain: props.chains,
    tags: props.tags,
  })),
  defaultSortBy: {
    key: 'usdValue',
  },
});

useBlockchainAccountLoading(fetchData);

onMounted(() => {
  nextTick(() => fetchData());
});

defineExpose({
  refresh: fetchData,
});
</script>

<template>
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
</template>
