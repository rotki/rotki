import type {
  BlockchainAccountBalance,
  EthereumValidator,
  XpubData,
} from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { isErr } from 'plainfp/result';
import { getAccountAddress, isXpubAccount } from '@/modules/accounts/account-utils';
import { useAccountRemovals } from '@/modules/accounts/use-account-removals';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { isBlockchain } from '@/modules/core/common/chains';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

export type ShowConfirmationParams = {
  type: 'account';
  data: BlockchainAccountBalance;
} | {
  type: 'validator';
  data: EthereumValidator[];
};

interface EvmPayloadData {
  address: string;
  chains: string[];
  includeAllChains: boolean;
}

type Payload = {
  type: 'validator';
  data: string[];
} | {
  type: 'evm';
  data: EvmPayloadData;
} | {
  type: 'xpub';
  data: XpubData & { chain: string };
} | {
  type: 'account';
  data: {
    chain: string;
    address: string;
  };
};

/**
 * Builds the delete request a confirmed deletion should send.
 *
 * @remarks
 * What the user is deleting depends on how the row was displayed, not only on what it holds. A
 * group is deleted per chain when it shows exactly one, and agnostically (every chain, including
 * ones not on screen) when `chains` covers all of `allChains`. Between those, a group showing a
 * subset deletes only the chains it shows, so `includeAllChains` has to be false or the user loses
 * chains they could not see. Validators and xpubs have their own endpoints and short-circuit
 * before any of that. Virtual chains are filtered out throughout, since the backend has no such
 * chain to delete from.
 */
function toPayload(params: ShowConfirmationParams): Payload {
  if (params.type === 'validator') {
    return {
      data: params.data.map(item => item.publicKey),
      type: 'validator',
    };
  }

  const account = params.data;
  const address = getAccountAddress(account);

  if (account.type === 'group') {
    if (isXpubAccount(account)) {
      return {
        data: {
          ...account.data,
          chain: account.chains[0],
        },
        type: 'xpub',
      };
    }

    const { allChains, chains } = account;

    const allFilteredChains = allChains?.filter(isBlockchain);
    const filteredChains = chains.filter(isBlockchain);

    if (filteredChains.length === 1) {
      return {
        data: {
          address,
          chain: filteredChains[0],
        },
        type: 'account',
      };
    }

    if (allFilteredChains && allFilteredChains.length > filteredChains.length) {
      return {
        data: {
          address,
          chains: filteredChains,
          includeAllChains: false,
        },
        type: 'evm',
      };
    }

    return {
      data: {
        address,
        chains: filteredChains,
        includeAllChains: true,
      },
      type: 'evm',
    };
  }

  return {
    data: {
      address,
      chain: account.chain,
    },
    type: 'account',
  };
}

interface RemoveAccountsParams { addresses: string[]; chains: string[] }

interface UseAccountDeleteReturn {
  showConfirmation: (params: ShowConfirmationParams, onComplete?: () => void) => void;
  removeAccounts: (params: RemoveAccountsParams) => void;
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

  const removeAccounts = ({ addresses, chains }: RemoveAccountsParams): void => {
    const knownAccounts = { ...get(accounts) };
    const knownBalances = { ...get(balances) };
    const groupAddresses: string[] = [];

    for (const chain of chains) {
      const chainAccounts = knownAccounts[chain];
      if (chainAccounts) {
        const groupIds = chainAccounts
          .filter(account => addresses.includes(getAccountAddress(account)) && account.groupId && account.groupHeader)
          .map(account => account.groupId!);

        const groups = chainAccounts.filter(account => account.groupId && groupIds.includes(account.groupId));
        groupAddresses.push(...groups.map(account => getAccountAddress(account)));

        knownAccounts[chain] = chainAccounts.filter(
          account => !(
            addresses.includes(getAccountAddress(account)) || (account.groupId && groupIds.includes(account.groupId))
          ),
        );
      }

      const chainBalances = knownBalances[chain];
      if (!chainBalances)
        continue;

      for (const address of [...addresses, ...groupAddresses].filter(uniqueStrings)) {
        if (chainBalances[address])
          delete chainBalances[address];
      }
      knownBalances[chain] = chainBalances;
    }

    set(accounts, knownAccounts);
    set(balances, knownBalances);

    // A chain read already in flight is carrying a pre-delete snapshot; marking the chain makes
    // it drop its write instead of replacing the chain wholesale and resurrecting the account.
    chains.forEach(chain => invalidateChain(chain));
  };

  async function removeValidator(publicKeys: string[]): Promise<void> {
    await deleteEth2Validators(publicKeys);
    removeAccounts({ addresses: publicKeys, chains: [Blockchain.ETH2] });
  }

  async function removeGroupAccounts(
    category: string,
    { address, chains, includeAllChains }: EvmPayloadData,
  ): Promise<void> {
    if (includeAllChains) {
      const outcome = await removeAgnosticAccount(category, address);
      if (isErr(outcome))
        return;

      removeAccounts({ addresses: [address], chains });
    }
    else {
      // Submitted together, serialized by the removal lane rather than by a limiter here: one
      // per chain and one active chain at a time is the shape this call always had, now declared
      // once where the activity is, as the warning on `DECODE_LANE` requires.
      const outcomes = await Promise.all(chains.map(
        async chain => [chain, await removeAccount({ accounts: [address], chain })] as const,
      ));

      // A partial failure keeps the chains it could not delete, rather than dropping the whole row.
      const removed = outcomes.filter(([, outcome]) => !isErr(outcome)).map(([chain]) => chain);
      if (removed.length === 0)
        return;

      removeAccounts({
        addresses: [address],
        chains: removed,
      });
    }
  }

  async function removeSingleAccount({ address, chain }: { address: string; chain: string }): Promise<void> {
    const outcome = await removeAccount({
      accounts: [address],
      chain,
    });

    // A failed or cancelled removal leaves the account on the backend, so the row has to stay.
    if (isErr(outcome))
      return;

    removeAccounts({
      addresses: [address],
      chains: [chain],
    });
  }

  async function removeXpub(payload: XpubData & { chain: string }): Promise<void> {
    const outcome = await deleteXpub(payload);
    if (isErr(outcome))
      return;

    removeAccounts({
      addresses: [getAccountAddress({ data: payload })],
      chains: [payload.chain],
    });
  }

  /**
   * Builds the confirmation wording, naming exactly what {@link toPayload} will delete.
   *
   * @remarks
   * This repeats that function's case analysis, so a change to one that is not mirrored in the
   * other tells the user it is deleting something other than what it deletes.
   */
  function getConfirmationMessage(params: ShowConfirmationParams): string {
    if (params.type === 'validator') {
      const length = params.data.length;
      if (length > 1) {
        return t('account_balances.confirm_delete.description_multiple_validator', { length });
      }

      const { index, publicKey } = params.data[0];
      return t('account_balances.confirm_delete.description_validator', { index, publicKey });
    }

    const address = getAccountAddress(params.data);

    const account = params.data;

    if (account.type === 'group') {
      if (isXpubAccount(account))
        return t('account_balances.confirm_delete.description_xpub', { address });

      const { allChains, chains } = account;

      const allFilteredChains = allChains?.filter(isBlockchain);
      const filteredChains = chains.filter(isBlockchain);

      if (filteredChains.length === 1)
        return t('account_balances.confirm_delete.description_address', { address, chain: getChainName(filteredChains[0]) });

      if (allFilteredChains && allFilteredChains.length > filteredChains.length)
        return t('account_balances.confirm_delete.description_multiple_address', { address, chains: filteredChains.map(item => getChainName(item)).join(', '), length: filteredChains.length });

      return t('account_balances.confirm_delete.agnostic.description', { address });
    }

    return t('account_balances.confirm_delete.description_address', { address, chain: getChainName(account.chain) });
  }

  function showConfirmation(params: ShowConfirmationParams, onComplete?: () => void): void {
    const message = getConfirmationMessage(params);
    show({ message, title: t('account_balances.confirm_delete.title') }, async () => {
      const payload = toPayload(params);

      if (payload.type === 'account')
        await removeSingleAccount(payload.data);
      else if (payload.type === 'validator')
        await removeValidator(payload.data);
      else if (payload.type === 'xpub')
        await removeXpub(payload.data);
      else if (payload.type === 'evm')
        await removeGroupAccounts(payload.type, payload.data);

      onComplete?.();
    });
  }

  return {
    removeAccounts,
    showConfirmation,
  };
}
