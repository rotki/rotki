import type { FetchAccountsParams, RefreshAccountsParams } from '@/modules/accounts/use-account-operations';
import type { Module } from '@/modules/core/common/modules';
import { type Account, Blockchain } from '@rotki/common';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

/**
 * Carries what an addition produced into the follow-up work that has to run after it.
 *
 * @remarks
 * Handed to the completion callback once every payload entry has settled, successes and failures
 * alike, so the follow-up sees the whole addition rather than one address at a time.
 */
export interface AccountAdditionParams {
  addedAccounts: Account[];
  modulesToEnable?: Module[];
  /**
   * The chain the addition targeted, or `undefined` when it spanned every EVM chain. Absent means
   * "all", not "unknown": it is what sends the follow-up down the fetch-everything branch.
   */
  chain?: string;
  isXpub?: boolean;
}

type RefreshAccountsCallback = (params: RefreshAccountsParams) => Promise<void>;

type FetchAccountsCallback = (params?: FetchAccountsParams) => Promise<void>;

export interface UseAccountAdditionCompletionReturn {
  completeAccountAddition: (params: AccountAdditionParams, onRefreshAccounts: RefreshAccountsCallback, onFetchAccounts: FetchAccountsCallback) => Promise<void>;
}

/**
 * The follow-up work that runs once an account addition has settled: tags, balances, modules and
 * token detection for the accounts it added.
 */
export function useAccountAdditionCompletion(): UseAccountAdditionCompletionReturn {
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { trackAddedAddresses } = useBlockchainAccountsStore();
  const { fetchTags } = useTagOperations();
  const { enableModule } = useSettingsOperations();
  const { supportsTransactions } = useSupportedChains();

  /**
   * Brings newly added accounts up to date: tags, balances, modules, then token detection.
   *
   * @remarks
   * A targeted chain that cannot hold tokens takes its balances from the refresh here; every other
   * chain only reads accounts at this point and gets its balances from the chain jobs below, which
   * have to run after the modules are enabled. An addition spanning every EVM chain has no single
   * chain to refresh here, so its chains without detection get a plain query there instead.
   *
   * That job detects before it queries, and the order is not interchangeable: detection's cache
   * write deletes the address's default-label asset rows, the native coin among them, and only a
   * query afterwards puts it back.
   *
   * The chain jobs run concurrently rather than one at a time. Each is a detection plus a full
   * network query, so awaiting them in a loop would serialise around twenty of them on an
   * every-EVM-chain addition; `BALANCES_LANE` is where that concurrency is capped.
   *
   * Tags are re-read before anything else, because the add itself can have created system tags
   * (`Contract` among them) that nothing else would fetch.
   */
  const completeAccountAddition = async (
    params: AccountAdditionParams,
    onRefreshAccounts: RefreshAccountsCallback,
    onFetchAccounts: FetchAccountsCallback,
  ): Promise<void> => {
    const {
      addedAccounts,
      chain,
      isXpub,
      modulesToEnable,
    } = params;

    await fetchTags();

    trackAddedAddresses(addedAccounts.map(item => item.address));

    if (chain !== undefined && !supportsTransactions(chain)) {
      await onRefreshAccounts({ addresses: addedAccounts.map(item => item.address), blockchain: chain, isXpub });
    }
    else {
      await onFetchAccounts({ blockchain: chain, refreshEns: true });
    }

    if (modulesToEnable) {
      const ethAccounts = addedAccounts.filter(a => a.chain === Blockchain.ETH);
      for (const account of ethAccounts) {
        await enableModule({
          addresses: [account.address],
          enable: modulesToEnable,
        });
      }
    }

    const detectable = new Map<string, string[]>();
    const queryOnly = new Map<string, string[]>();
    for (const { address, chain: accountChain } of addedAccounts) {
      const group = supportsTransactions(accountChain) ? detectable : queryOnly;
      group.set(accountChain, [...group.get(accountChain) ?? [], address]);
    }

    await Promise.allSettled([
      ...Array.from(detectable, async ([accountChain, chainAddresses]) => refreshBlockchainBalances(
        { blockchain: accountChain },
        'background',
        { detect: true, detectAddresses: chainAddresses },
      )),
      ...(chain === undefined
        ? Array.from(queryOnly, async ([accountChain, chainAddresses]) => refreshBlockchainBalances(
            { addresses: chainAddresses, blockchain: accountChain },
            'background',
          ))
        : []),
    ]);
  };

  return { completeAccountAddition };
}
