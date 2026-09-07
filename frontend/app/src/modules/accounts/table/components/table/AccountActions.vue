<script setup lang="ts" generic="T extends BlockchainAccountBalance">
import type { AccountDataRow } from '../../types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import TokenDetection from '@/modules/accounts/blockchain/TokenDetection.vue';
import AccountSkipQueriesToggle from '@/modules/accounts/table/components/table/AccountSkipQueriesToggle.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import RowActions from '@/modules/shell/components/RowActions.vue';

/**
 * Referenced only through inferred types; the export is required for declaration emit.
 *
 * @public
 */
export interface Props<T extends BlockchainAccountBalance> {
  accountOperation: boolean;
  group?: 'evm' | 'xpub';
  isSectionLoading: boolean;
  isVirtual: boolean;
  row: AccountDataRow<T>;
}

const { isVirtual, row } = defineProps<Props<T>>();

const emit = defineEmits<{
  delete: [row: AccountDataRow<T>];
  edit: [group: string | undefined, row: AccountDataRow<T>];
}>();

const { t } = useI18n({ useScope: 'global' });
const { supportsTransactions } = useSupportedChains();

function showTokenDetection(row: AccountDataRow<T>): boolean {
  if (row.type === 'group')
    return row.chains.some(chain => supportsTransactions(chain));

  return supportsTransactions(row.chain);
}

/**
 * The chains a skip rule from this row applies to: every chain the row stands for.
 *
 * @remarks
 * Deliberately not the chains the Chains column currently *shows*. Its icons are a display filter -
 * clicking one drops that chain from the row's totals - so scoping the action to what survives it
 * would make the same control mean two things, and dimming a chain to read the value without it
 * would then skip every chain except that one. The page's own chain filter still narrows the row,
 * because it narrows what the row is.
 */
const skipChains = computed<string[]>(() => row.type === 'group' ? row.chains : [row.chain]);

/**
 * Skipping is keyed on an address, so it is offered for address accounts only.
 *
 * @remarks
 * A validator row carries a public key and an xpub group its xpub, neither of which the backend
 * matches a rule against. The addresses derived from an xpub are reachable on its virtual rows,
 * which carry no actions at all, for the same reason edit and delete skip them.
 */
const canSkipQueries = computed<boolean>(() => !isVirtual && row.data.type === 'address' && get(skipChains).length > 0);

function getTokenDetectionChains(row: AccountDataRow<T>): string[] {
  if (row.type === 'group')
    return row.chains.filter(chain => supportsTransactions(chain));

  return [row.chain];
}
</script>

<template>
  <div class="flex justify-end mr-2">
    <TokenDetection
      v-if="showTokenDetection(row)"
      class="ms-2"
      :address="getAccountAddress(row)"
      :loading="isSectionLoading"
      :chains="getTokenDetectionChains(row)"
    />
    <AccountSkipQueriesToggle
      v-if="canSkipQueries"
      :address="getAccountAddress(row)"
      :chains="skipChains"
      :disabled="accountOperation"
    />
    <RowActions
      v-if="!isVirtual"
      :edit-tooltip="t('account_balances.edit_tooltip')"
      :disabled="accountOperation"
      :no-edit="group !== 'evm'"
      @edit-click="emit('edit', group, row)"
      @delete-click="emit('delete', row)"
    />
  </div>
</template>
