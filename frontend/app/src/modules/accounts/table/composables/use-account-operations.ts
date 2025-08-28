import type { AccountDataRow } from '../types';
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import { type ShowConfirmationParams, useAccountDelete } from '@/composables/accounts/blockchain/use-account-delete';
import { type AccountManageState, editBlockchainAccount } from '@/composables/accounts/blockchain/use-account-manage';
import { useAddressBookForm } from '@/composables/address-book/form';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { getAccountAddress, getChain } from '@/utils/blockchain/accounts/utils';

interface AccountOperationCallbacks {
  onEdit: (account: AccountManageState) => void;
  onRefresh: () => void;
}

interface UseAccountOperationsReturn<T extends BlockchainAccountBalance> {
  confirmDelete: (item: AccountDataRow<T>) => void;
  edit: (group: string | undefined, row: AccountDataRow<T>) => Promise<void>;
  handleXpubChildEdit: (row: AccountDataRow<T>) => Promise<void>;
  showConfirmation: (params: ShowConfirmationParams) => void;
}

export function useAccountOperations<T extends BlockchainAccountBalance>(
  callbacks: AccountOperationCallbacks,
): UseAccountOperationsReturn<T> {
  const { showConfirmation } = useAccountDelete();
  const { showGlobalDialog } = useAddressBookForm();
  const { getAddressesNames } = useAddressesNamesApi();

  function confirmDelete(item: AccountDataRow<T>): void {
    showConfirmation(
      {
        data: item,
        type: 'account',
      },
      () => {
        callbacks.onRefresh();
      },
    );
  }

  async function handleXpubChildEdit(row: AccountDataRow<T>): Promise<void> {
    const blockchain = getChain(row);
    if (!blockchain)
      return;

    let name = '';
    const address = getAccountAddress(row);
    const savedNames = await getAddressesNames([
      {
        address,
        blockchain,
      },
    ]);
    if (savedNames.length > 0)
      name = savedNames[0].name;

    showGlobalDialog({
      address,
      blockchain,
      name,
    });
  }

  async function edit(group: string | undefined, row: AccountDataRow<T>): Promise<void> {
    if (group === 'evm') {
      callbacks.onEdit(editBlockchainAccount(row));
    }
    else if (group === 'xpub') {
      await handleXpubChildEdit(row);
    }
  }

  return {
    confirmDelete,
    edit,
    handleXpubChildEdit,
    showConfirmation,
  };
}
