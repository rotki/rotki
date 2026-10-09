<script setup lang="ts" generic="T extends BlockchainAccountBalance">
import type { AccountDataRow } from '../../types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress, isAddressAccount } from '@/modules/accounts/account-utils';
import TokenDetection from '@/modules/accounts/blockchain/TokenDetection.vue';
import { useAccountDelete } from '@/modules/accounts/blockchain/use-account-delete';
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
  row: AccountDataRow<T>;
}

const { row } = defineProps<Props<T>>();

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
 * matches a rule against.
 */
const canSkipQueries = computed<boolean>(() => isAddressAccount(row) && get(skipChains).length > 0);

function getTokenDetectionChains(row: AccountDataRow<T>): string[] {
  if (row.type === 'group')
    return row.chains.filter(chain => supportsTransactions(chain));

  return [row.chain];
}

const menuOpen = ref<boolean>(false);

/** Delete asks in place, inside the menu, rather than in a dialog over the page. */
const confirmingDelete = ref<boolean>(false);

const { describeDeletion } = useAccountDelete();

/** Read only while confirming, so rows that never ask do not plan a deletion. */
const deletionText = computed<string>(() => describeDeletion({ data: row, type: 'account' }));

function confirmDeletion(): void {
  set(menuOpen, false);
  set(confirmingDelete, false);
  emit('delete', row);
}

watch(menuOpen, (open) => {
  if (!open)
    set(confirmingDelete, false);
});
</script>

<template>
  <!-- edit stays on the row; the occasional per-account upkeep sits behind the menu -->
  <div class="flex justify-end items-center gap-1 mr-2">
    <RowActions
      :edit-tooltip="t('account_balances.edit_tooltip')"
      :disabled="accountOperation"
      :no-edit="group !== 'evm'"
      no-delete
      @edit-click="emit('edit', group, row)"
    />
    <RuiMenu
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="attrs"
          variant="text"
          icon
          :aria-label="t('account_balances.row_menu')"
          data-testid="account-row-menu"
        >
          <RuiIcon
            size="16"
            name="lu-ellipsis-vertical"
          />
        </RuiButton>
      </template>
      <div class="w-80 py-1">
        <TokenDetection
          v-if="showTokenDetection(row)"
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
        <RuiDivider
          v-if="showTokenDetection(row) || canSkipQueries"
          class="my-1"
        />
        <div
          v-if="confirmingDelete"
          class="mx-2 my-1 rounded-md bg-rui-error/10 px-3 py-2"
          data-testid="row-delete-confirm"
        >
          <div class="text-body-2 font-medium">
            {{ t('account_balances.confirm_delete.title') }}
          </div>
          <div class="text-caption text-rui-text-secondary break-words">
            {{ deletionText }}
          </div>
          <div class="flex justify-end gap-2 mt-2">
            <RuiButton
              size="sm"
              variant="text"
              @click="confirmingDelete = false"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
            <RuiButton
              size="sm"
              color="error"
              data-testid="row-delete-confirm-run"
              @click="confirmDeletion()"
            >
              {{ t('common.actions.delete') }}
            </RuiButton>
          </div>
        </div>
        <RuiButton
          v-else
          variant="list"
          color="error"
          :disabled="accountOperation"
          data-testid="row-delete"
          @click="confirmingDelete = true"
        >
          <template #prepend>
            <RuiIcon
              size="18"
              name="lu-trash-2"
            />
          </template>
          {{ t('common.actions.delete') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
