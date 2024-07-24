<script setup lang="ts">
import { getAccountAddress } from '@/utils/blockchain/accounts';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type {
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

const props = defineProps<{
  groupId: string;
  chains?: string[];
  tags?: string[];
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
} = usePaginationFilters<BlockchainAccountWithBalance, BlockchainAccountGroupRequestPayload>(
  null,
  false,
  useEmptyFilter,
  fetchGroupAccounts,
  {
    extraParams: computed(() => ({
      groupId: props.groupId,
      chain: props.chains ?? [],
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
</script>

<template>
  <div class="bg-white dark:bg-[#1E1E1E] rounded-xl my-2">
    <AccountBalancesTable
      v-model:pagination="pagination"
      v-model:sort="sort"
      :accounts="accounts"
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
  </div>
</template>
