<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import type { LocationQuery } from '@/modules/core/table/route';
import { getAccountAddress, getGroupId, isXpubAccount } from '@/modules/accounts/account-utils';
import AccountBalanceAggregatedAssets from '@/modules/accounts/AccountBalanceAggregatedAssets.vue';
import AccountGroupDetails from '@/modules/accounts/AccountGroupDetails.vue';
import AccountGroupDetailsTable from '@/modules/accounts/AccountGroupDetailsTable.vue';
import AccountBalanceDetails from '@/modules/accounts/balances/AccountBalanceDetails.vue';

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

const detailsTable = useTemplateRef<ComponentExposed<typeof AccountGroupDetailsTable>>('detailsTable');

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
    :is-xpub="isXpubAccount(row)"
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
        :group="isXpubAccount(row) ? 'xpub' : undefined"
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
