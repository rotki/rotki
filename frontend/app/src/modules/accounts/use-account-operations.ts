import type { MaybeRef } from 'vue';
import type { AddressBookSimplePayload } from '@/modules/accounts/address-book/eth-names';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { allWithConcurrency, type ResultAsync } from 'plainfp/result-async';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { useAccountFetching } from '@/modules/accounts/use-account-fetching';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

/** Chains read at a time during the account walk. */
const ACCOUNT_READ_CONCURRENCY = 2;

export interface RefreshAccountsParams {
  blockchain?: MaybeRef<string>;
  addresses?: string[];
  isXpub?: boolean;
  periodic?: boolean;
}

interface UseAccountOperationsReturn {
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (params?: RefreshAccountsParams) => Promise<void>;
}

export function useAccountOperations(): UseAccountOperationsReturn {
  const { fetch } = useAccountFetching();
  const { hydrate } = useBalanceHydration();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { fetchEnsNames } = useEnsOperations();
  const { detectEvmAccounts: detectEvmAccountsCaller } = useBlockchainAccountsApi();
  const { isEvm, supportedChains, supportsTransactions } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();

  const { track } = useAccountLoadState();
  const { submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * Two chains at a time.
   *
   * ⭐ Bounded by `allWithConcurrency` rather than a semaphore. The fit is structural: the chain
   * set is a fixed batch known upfront, with no dynamic arrival, no cancel and no progress —
   * precisely the case the orchestrator is *not* for (`scheduler.ts:41` draws the same boundary
   * from the other side). The bound is a function call, so there is no second scheduler and no
   * lane to mistake for an ordering.
   *
   * 🔴 `allWithConcurrency` **short-circuits on the first `err`**: in-flight factories finish and
   * no new ones start. One chain failing must not abandon the other sixteen, so each factory is
   * infallible — `ResultAsync<void, never>`. Nothing in the package enforces that, and the naive
   * call site silently drops chains.
   */
  const readChains = async (chains: string[], onChainRead?: (chain: string) => void): Promise<void> => {
    const factories = chains.map(chain => async (): ResultAsync<void, never> => {
      try {
        await fetch(chain);
        // ⭐ Per chain, not per walk. This chain's accounts are known now, and nothing about its
        // balances depends on the other sixteen — so handing it downstream here is what stops the
        // slowest chain from gating every other chain's balances.
        onChainRead?.(chain);
      }
      catch (error: unknown) {
        // Swallowed rather than rethrown: a rejection here is a rejection of the whole batch. The
        // paths `fetch` owns already notify; this covers the ones it does not.
        logger.error(error);
      }
      return ok(undefined);
    });

    await allWithConcurrency(factories, ACCOUNT_READ_CONCURRENCY);
  };

  const fetchAccounts = async (blockchain?: string | string[], refreshEns: boolean = false): Promise<void> => {
    let chains: string[];
    if (blockchain)
      chains = Array.isArray(blockchain) ? blockchain : [blockchain];
    else
      chains = get(supportedChains).map(chain => chain.id);

    // 🔴 eth2 leaves the full walk. Every other chain is a plain `GET .../accounts`; eth2 is a
    // backend task that re-queries validators, so it is both the slowest leg and the only one that
    // is not an accounts read. Inside `readChains` it gated the whole `Promise.all`, which made
    // every consumer of account readiness — including the balance refresh — wait on a validator
    // query. Observed after a re-login: 17 chains' accounts landed, and not one balance was
    // fetched, because the walk never resolved.
    //
    // Its own read still happens, just not as something the rest of the load waits on. A consumer
    // that reaches eth2 before it lands now sees the chain as *unknown* rather than empty, which
    // `clearChainBalances` refuses to act on.
    if (!blockchain && chains.includes(Blockchain.ETH2)) {
      chains = chains.filter(chain => chain !== Blockchain.ETH2);
      startPromise(fetch(Blockchain.ETH2));
    }

    // Only a full read is tracked: that is the one that leaves the store partially filled for long
    // enough for a consumer to snapshot it. A targeted read is already scoped to what it changed.
    //
    // ⭐ On the full walk each chain's data refresh runs as that chain's accounts land, rather than
    // all of them after all seventeen. A targeted read keeps its old shape — `refreshAccounts`
    // still drives balances for the chain it was asked about.
    //
    // These stand alone: independent, deduplicated by chain, and deliberately NOT under an
    // umbrella. A data refresh from the DB is plumbing, not work — the umbrella belongs to the job
    // (detection and the network query), which is what a user watches, cancels or supersedes.
    //
    // Not awaited either: the caller waits for *accounts*, and a chain's balances arriving later is
    // the point.
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

    return addresses.filter(uniqueStrings);
  };

  const refreshAccounts = async (params: RefreshAccountsParams = {}): Promise<void> => {
    const { addresses, blockchain, isXpub = false, periodic = false } = params;
    const chain = get(blockchain);
    const uniqueAddresses = targetAddresses(addresses, chain);
    await fetchAccounts(chain, true);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const shouldRefresh = !!(isEth2 || uniqueAddresses);
    // ⚠️ On the full walk `fetchAccounts` has already hydrated each chain as that chain landed, so
    // repeating the sweep here would read every chain a second time. A targeted refresh still
    // drives its own chain: nothing else will.
    const pending: Promise<any>[] = [];
    if (shouldRefresh)
      pending.push(refreshBlockchainBalances({ addresses: uniqueAddresses, blockchain: chain, isXpub }, periodic ? 'periodic' : 'background'));
    else if (chain !== undefined)
      pending.push(hydrate({ addresses: uniqueAddresses, blockchain: chain, isXpub }));

    if (isEth && getAddresses(Blockchain.ETH2).length > 0)
      startPromise(refreshAccounts({ blockchain: Blockchain.ETH2 }));

    await Promise.allSettled(pending);
  };

  const detectEvmAccounts = async (): Promise<void> => {
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.DETECT),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<unknown>(
          async () => detectEvmAccountsCaller(),
        ),
        () => {},
      ),
      subtitle: activityLabel(ActivityKind.ACCOUNTS, ActivityPart.DETECT),
      title: t('task_center.group.accounts'),
    });

    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      notifyError(
        t('actions.detect_evm_accounts.error.title'),
        t('actions.detect_evm_accounts.error.message', {
          message: outcome.error.message,
        }),
      );
    }
  };

  return {
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
  };
}
