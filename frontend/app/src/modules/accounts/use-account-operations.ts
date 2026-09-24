import type { MaybeRef } from 'vue';
import type { AddressBookSimplePayload } from '@/modules/accounts/address-book/eth-names';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { ok } from 'plainfp/result';
import { allWithConcurrency, type ResultAsync } from 'plainfp/result-async';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { useAccountFetching } from '@/modules/accounts/use-account-fetching';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

/** Chains read at a time during the account walk. */
const ACCOUNT_READ_CONCURRENCY = 2;

export interface FetchAccountsParams {
  /** Omit for the full walk over every supported chain. */
  blockchain?: string | string[];
  /** Re-resolve ENS names for the chains that were read. */
  refreshEns?: boolean;
}

export interface RefreshAccountsParams {
  blockchain: MaybeRef<string>;
  addresses?: string[];
  isXpub?: boolean;
  periodic?: boolean;
}

interface UseAccountOperationsReturn {
  fetchAccounts: (params?: FetchAccountsParams) => Promise<void>;
  refreshAccounts: (params: RefreshAccountsParams) => Promise<void>;
}

export function useAccountOperations(): UseAccountOperationsReturn {
  const { fetch } = useAccountFetching();
  const { hydrate } = useBalanceHydration();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { fetchEnsNames } = useEnsOperations();
  const { isEvm, supportedChains, supportsTransactions } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();

  const { track } = useAccountLoadState();

  /**
   * Reads each chain's accounts, {@link ACCOUNT_READ_CONCURRENCY} at a time.
   *
   * @remarks
   * `onChainRead` fires as each chain lands, so a caller can act on one chain without waiting for
   * the rest. A targeted read omits it, being already scoped to what it changed.
   */
  const readChains = async (chains: string[], onChainRead?: (chain: string) => void): Promise<void> => {
    const factories = chains.map(chain => async (): ResultAsync<void, never> => {
      try {
        await fetch(chain);
        onChainRead?.(chain);
      }
      catch (error: unknown) {
        logger.error(error);
      }
      return ok(undefined);
    });

    await allWithConcurrency(factories, ACCOUNT_READ_CONCURRENCY);
  };

  const fetchAccounts = async (params: FetchAccountsParams = {}): Promise<void> => {
    const { blockchain, refreshEns = false } = params;
    let chains: string[];
    if (blockchain)
      chains = Array.isArray(blockchain) ? blockchain : [blockchain];
    else
      chains = get(supportedChains).map(chain => chain.id);

    if (!blockchain && chains.includes(Blockchain.ETH2)) {
      chains = chains.filter(chain => chain !== Blockchain.ETH2);
      startPromise(fetch(Blockchain.ETH2));
    }

    const hydrateChain = (chain: string): void => {
      startPromise(hydrate({ blockchain: chain }));
    };

    const read = readChains(chains, blockchain ? undefined : hydrateChain);
    await (blockchain ? read : track(read));

    const namesPayload: AddressBookSimplePayload[] = [];

    chains.forEach((chain) => {
      if (!isEvm(chain))
        return;

      const addresses = getAddresses(chain);
      namesPayload.push(...addresses.map(address => ({ address, blockchain: chain })));
    });

    if (namesPayload.length > 0)
      startPromise(fetchEnsNames(namesPayload, refreshEns));
  };

  /**
   * Chains that support transactions are refreshed wholesale, so only the others narrow to the given
   * addresses.
   */
  const targetAddresses = (addresses: string[] | undefined, chain: string | undefined): string[] | undefined => {
    if (!addresses?.length || !chain || supportsTransactions(chain))
      return undefined;

    return [...new Set(addresses)];
  };

  /**
   * Read one chain's accounts, then bring its balances up to date. For the walk over every chain,
   * call {@link fetchAccounts} instead.
   */
  const refreshAccounts = async (params: RefreshAccountsParams): Promise<void> => {
    const { addresses, blockchain, isXpub = false, periodic = false } = params;
    const chain = get(blockchain);
    const uniqueAddresses = targetAddresses(addresses, chain);
    await fetchAccounts({ blockchain: chain, refreshEns: true });

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const shouldRefresh = !!(isEth2 || uniqueAddresses);
    const pending: Promise<any>[] = [];
    if (shouldRefresh)
      pending.push(refreshBlockchainBalances({ addresses: uniqueAddresses, blockchain: chain, isXpub }, periodic ? RefreshMode.PERIODIC : RefreshMode.BACKGROUND));
    else if (chain !== undefined)
      pending.push(hydrate({ addresses: uniqueAddresses, blockchain: chain, isXpub }));

    if (isEth && getAddresses(Blockchain.ETH2).length > 0)
      startPromise(refreshAccounts({ blockchain: Blockchain.ETH2 }));

    await Promise.allSettled(pending);
  };

  return {
    fetchAccounts,
    refreshAccounts,
  };
}
