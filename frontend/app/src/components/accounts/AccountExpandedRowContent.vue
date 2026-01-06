<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type { BlockchainAccountGroupWithBalance } from '@/types/blockchain/accounts';
import type { LocationQuery } from '@/types/route';
import AccountBalanceAggregatedAssets from '@/components/accounts/AccountBalanceAggregatedAssets.vue';
import AccountGroupDetails from '@/components/accounts/AccountGroupDetails.vue';
import AccountGroupDetailsTable from '@/components/accounts/AccountGroupDetailsTable.vue';
import AccountBalanceDetails from '@/components/accounts/balances/AccountBalanceDetails.vue';
import { getAccountAddress, getGroupId } from '@/utils/blockchain/accounts/utils';

const tab = defineModel<number>('tab', { required: true });
const query = defineModel<LocationQuery>('query', { required: true });
const selectedAssets = defineModel<string[] | undefined>('selectedAssets', { required: true });

defineProps<{
  row: BlockchainAccountGroupWithBalance;
  visibleTags: string[];
  chains: string[];
  selectionMode: boolean;
}>();

const emit = defineEmits<{
  edit: [account: AccountManageState];
}>();

const detailsTable = ref<ComponentExposed<typeof AccountGroupDetailsTable>>();

async function refresh(): Promise<void> {
  if (!isDefined(detailsTable))
    return;

  await get(detailsTable).refresh();
}

defineExpose({
  refresh,
});
</script>

<template>
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
        :chains="chains"
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
        :chains="chains"
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
