<script setup lang="ts" generic="T extends BlockchainAccountBalance">
import type { AccountDataRow } from '../../types';
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import TokenDetection from '@/components/accounts/blockchain/TokenDetection.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

export interface Props<T extends BlockchainAccountBalance> {
  accountOperation: boolean;
  group?: 'evm' | 'xpub';
  isOnlyShowingLoopringChain: boolean;
  isSectionLoading: boolean;
  isVirtual: boolean;
  row: AccountDataRow<T>;
}

defineProps<Props<T>>();

const emit = defineEmits<{
  delete: [row: AccountDataRow<T>];
  edit: [group: string | undefined, row: AccountDataRow<T>];
}>();

const { t } = useI18n({ useScope: 'global' });
const { supportsTransactions } = useSupportedChains();

function showTokenDetection(row: AccountDataRow<T>): boolean {
  if (row.type === 'group')
    return row.chains.length === 1 && supportsTransactions(row.chains[0]);

  return supportsTransactions(row.chain);
}
</script>

<template>
  <div class="flex justify-end mr-2">
    <TokenDetection
      v-if="showTokenDetection(row)"
      class="ms-2"
      :address="getAccountAddress(row)"
      :loading="isSectionLoading"
      :chain="row.type === 'group' ? row.chains[0] : row.chain"
    />
    <RowActions
      v-if="!isVirtual && !isOnlyShowingLoopringChain"
      class="account-balance-table__actions"
      :edit-tooltip="t('account_balances.edit_tooltip')"
      :disabled="accountOperation"
      @edit-click="emit('edit', group, row)"
      @delete-click="emit('delete', row)"
    />
  </div>
</template>
