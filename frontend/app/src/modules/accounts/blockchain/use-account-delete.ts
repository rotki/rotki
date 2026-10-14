import { Blockchain } from '@rotki/common';
import { pipe } from 'plainfp';
import { fromArray } from 'plainfp/non-empty-array';
import { map as mapOption, none, type Option, some, tap as tapOption } from 'plainfp/option';
import { isOk, map as mapResult, toOption } from 'plainfp/result';
import {
  type AccountDeletion,
  DeletionKind,
  planDeletion,
  removedAccounts,
  type RemovedAccounts,
  removedChains,
  removedXpub,
  type ShowConfirmationParams,
  withoutRemoved,
} from '@/modules/accounts/core/account-deletion';
import { useAccountRemovals } from '@/modules/accounts/use-account-removals';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAccountDeleteReturn {
  showConfirmation: (params: ShowConfirmationParams, onComplete?: () => void) => void;
  /** What deleting would remove, for a confirmation the caller shows itself, such as an inline one. */
  describeDeletion: (params: ShowConfirmationParams) => string;
  /** Deletes at once, for a caller that has already confirmed with the user. */
  deleteConfirmed: (params: ShowConfirmationParams, onComplete?: () => void) => Promise<void>;
}

export function useAccountDelete(): UseAccountDeleteReturn {
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { balances } = storeToRefs(useBalancesStore());
  const { invalidateChain } = useBlockchainAccountsStore();
  const { deleteEth2Validators } = useEthStaking();
  const { deleteXpub, removeAccount, removeAgnosticAccount } = useAccountRemovals();
  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
  const { getChainName } = useSupportedChains();

  function prune(removed: RemovedAccounts): void {
    const remaining = withoutRemoved({ accounts: get(accounts), balances: get(balances) }, removed);
    set(accounts, remaining.accounts);
    set(balances, remaining.balances);
    removedChains(removed).forEach(chain => invalidateChain(chain));
  }

  async function removeFromChains(address: string, chains: string[]): Promise<Option<RemovedAccounts>> {
    const outcomes = await Promise.all(chains.map(
      async chain => ({ chain, outcome: await removeAccount({ accounts: [address], chain }) }),
    ));

    return pipe(
      fromArray(outcomes.filter(({ outcome }) => isOk(outcome)).map(({ chain }) => chain)),
      mapOption(goneFromTheBackend => removedAccounts([address], goneFromTheBackend)),
    );
  }

  /** Sends the delete, resolving to what the backend no longer tracks, or none when nothing left it. */
  async function execute(deletion: AccountDeletion): Promise<Option<RemovedAccounts>> {
    switch (deletion.kind) {
      case DeletionKind.VALIDATORS: {
        const publicKeys = deletion.validators.map(validator => validator.publicKey);
        const deleted = await deleteEth2Validators(publicKeys);
        return deleted ? some(removedAccounts(publicKeys, [Blockchain.ETH2])) : none;
      }
      case DeletionKind.XPUB: {
        const { chain, key } = deletion;
        const outcome = await deleteXpub({ chain, derivationPath: key.derivationPath, xpub: key.xpub });
        return toOption(mapResult(outcome, () => removedXpub(key, chain)));
      }
      case DeletionKind.ON_CHAIN:
        return removeFromChains(deletion.address, [deletion.chain]);
      case DeletionKind.ON_CHAINS:
        return removeFromChains(deletion.address, deletion.chains);
      case DeletionKind.EVERYWHERE: {
        const { address, category, chains } = deletion;
        const outcome = await removeAgnosticAccount(category, address);
        return toOption(mapResult(outcome, () => removedAccounts([address], chains)));
      }
    }
  }

  function describe(deletion: AccountDeletion): string {
    switch (deletion.kind) {
      case DeletionKind.VALIDATORS: {
        const { validators } = deletion;
        if (validators.length > 1)
          return t('account_balances.confirm_delete.description_multiple_validator', { length: validators.length });

        const { index, publicKey } = validators[0];
        return t('account_balances.confirm_delete.description_validator', { index, publicKey });
      }
      case DeletionKind.XPUB:
        return t('account_balances.confirm_delete.description_xpub', { address: deletion.key.xpub });
      case DeletionKind.ON_CHAIN:
        return t('account_balances.confirm_delete.description_address', { address: deletion.address, chain: getChainName(deletion.chain) });
      case DeletionKind.ON_CHAINS: {
        const { address, chains } = deletion;
        return t('account_balances.confirm_delete.description_multiple_address', {
          address,
          chains: chains.map(chain => getChainName(chain)).join(', '),
          length: chains.length,
        });
      }
      case DeletionKind.EVERYWHERE:
        return t('account_balances.confirm_delete.agnostic.description', { address: deletion.address });
    }
  }

  function showConfirmation(params: ShowConfirmationParams, onComplete?: () => void): void {
    const deletion = planDeletion(params);
    show({ message: describe(deletion), title: t('account_balances.confirm_delete.title') }, async () => {
      pipe(await execute(deletion), tapOption(prune));
      onComplete?.();
    });
  }

  function describeDeletion(params: ShowConfirmationParams): string {
    return describe(planDeletion(params));
  }

  async function deleteConfirmed(params: ShowConfirmationParams, onComplete?: () => void): Promise<void> {
    pipe(await execute(planDeletion(params)), tapOption(prune));
    onComplete?.();
  }

  return {
    deleteConfirmed,
    describeDeletion,
    showConfirmation,
  };
}
