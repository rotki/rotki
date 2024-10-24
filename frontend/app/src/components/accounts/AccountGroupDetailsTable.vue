<script setup lang="ts">
import { type LocationQuery, RouterExpandedIdsSchema } from '@/types/route';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type {
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

const query = defineModel<LocationQuery>('query', { required: false, default: () => ({}) });

const props = defineProps<{
  groupId: string;
  chains: string[];
  tags?: string[];
  isEvm: boolean;
}>();

const emit = defineEmits<{
  (e: 'edit', account: AccountManageState): void;
}>();

const expanded = ref<string[]>([]);

const { fetchGroupAccounts } = useBlockchainStore();

const {
  state: accounts,
  fetchData,
  pagination,
  sort,
} = usePaginationFilters<BlockchainAccountWithBalance, BlockchainAccountGroupRequestPayload>(fetchGroupAccounts, {
  history: 'external',
  extraParams: computed(() => ({
    expanded: get(expanded).join(','),
  })),
  onUpdateFilters(query) {
    const { expanded: expandedIds } = RouterExpandedIdsSchema.parse(query);
    set(expanded, expandedIds);
  },
  requestParams: computed(() => ({
    groupId: props.groupId,
    chain: props.chains,
    tags: props.tags,
  })),
  defaultSortBy: {
    column: 'value',
    direction: 'desc',
  },
  query,
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
    v-model:expanded-ids="expanded"
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
