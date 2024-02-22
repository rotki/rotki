<script setup lang="ts">
import { getAccountAddress } from '@/utils/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type {
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

const props = defineProps<{ groupId: string }>();

const { fetchGroupAccounts } = useBlockchainStore();

const {
  options,
  state: accounts,
  fetchData,
  setTableOptions,
} = usePaginationFilters<
    BlockchainAccountWithBalance,
    BlockchainAccountGroupRequestPayload,
    BlockchainAccountWithBalance,
    Collection<BlockchainAccountWithBalance>
>(
  null,
  false,
  useEmptyFilter,
  fetchGroupAccounts,
  {
    extraParams: computed(() => ({
      groupId: props.groupId,
    })),
  },
);

useBlockchainAccountLoading(fetchData);

onMounted(() => {
  nextTick(() => fetchData());
});
</script>

<template>
  <div class="bg-white dark:bg-[#1E1E1E]">
    <AccountBalancesTable
      :accounts="accounts"
      :options="options"
      @update:options="setTableOptions($event)"
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
