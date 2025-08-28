<script setup lang="ts">
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type {
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';
import AccountBalanceDetails from '@/components/accounts/balances/AccountBalanceDetails.vue';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { AccountBalancesTable } from '@/modules/accounts/table';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { type LocationQuery, RouterExpandedIdsSchema } from '@/types/route';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

const query = defineModel<LocationQuery>('query', { default: () => ({}), required: false });

const props = defineProps<{
  groupId: string;
  chains: string[];
  tags?: string[];
  category: string;
}>();

const emit = defineEmits<{
  edit: [account: AccountManageState];
}>();

const { category } = toRefs(props);

const expanded = ref<string[]>([]);

const { fetchGroupAccounts } = useBlockchainAccountData();

const {
  fetchData,
  pagination,
  sort,
  state: accounts,
} = usePaginationFilters<BlockchainAccountWithBalance, BlockchainAccountGroupRequestPayload>(fetchGroupAccounts, {
  defaultSortBy: {
    column: 'usdValue',
    direction: 'desc',
  },
  extraParams: computed(() => ({
    expanded: get(expanded).join(','),
  })),
  history: 'external',
  onUpdateFilters(query) {
    const { expanded: expandedIds } = RouterExpandedIdsSchema.parse(query);
    set(expanded, expandedIds);
  },
  query,
  requestParams: computed(() => ({
    chain: props.chains,
    groupId: props.groupId,
    tags: props.tags,
  })),
});

useBlockchainAccountLoading(category);

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
    :category="category"
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
