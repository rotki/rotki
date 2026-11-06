import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress, getChain } from '@/modules/accounts/account-utils';
import { useAddressBookForm } from '@/modules/accounts/address-book/use-address-book-form';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { useAccountDelete } from '@/modules/accounts/blockchain/use-account-delete';
import { type AccountManageState, editBlockchainAccount } from '@/modules/accounts/blockchain/use-account-manage';

interface AccountOperationCallbacks {
  onEdit: (account: AccountManageState) => void;
  onRefresh: () => void;
}

interface UseAccountOperationsReturn<T extends BlockchainAccountBalance> {
  /** Deletes a row the user already confirmed, inline in its actions menu. */
  deleteAccount: (item: AccountDataRow<T>) => Promise<void>;
  edit: (group: string | undefined, row: AccountDataRow<T>) => Promise<void>;
  handleXpubChildEdit: (row: AccountDataRow<T>) => Promise<void>;
}

export function useAccountOperations<T extends BlockchainAccountBalance>(
  callbacks: AccountOperationCallbacks,
): UseAccountOperationsReturn<T> {
  const { deleteConfirmed } = useAccountDelete();
  const { showGlobalDialog } = useAddressBookForm();
  const { getAddressesNames } = useAddressesNamesApi();

  async function deleteAccount(item: AccountDataRow<T>): Promise<void> {
    await deleteConfirmed({ data: item, type: 'account' });
    callbacks.onRefresh();
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
    deleteAccount,
    edit,
    handleXpubChildEdit,
  };
}
