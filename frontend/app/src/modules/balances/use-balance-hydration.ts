import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { allWithConcurrency, type ResultAsync, retry, type RetryOptions } from 'plainfp/result-async';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useBalanceProcessingService } from '@/modules/balances/services/use-balance-processing-service';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

/**
 * Chains hydrated at a time. Hydration's own bound and nowhere else's — never a lane, and never
 * the same piece of work bounded twice (the `DECODE_LANE` trap).
 */
const HYDRATION_CONCURRENCY = 4;

/**
 * A failed read is retried silently: hydration is plumbing, so a transient failure is not the
 * user's problem to act on. Only a failure worth another attempt reaches this — see `readOnce`.
 */
const HYDRATION_RETRY: RetryOptions = { backoff: 'exponential', delayMs: 500, times: 3 };

interface UseBalanceHydrationReturn {
  /**
   * Repopulate the store from the user's own database, one read per chain. Resolves when every
   * chain in the payload has settled.
   */
  hydrate: (payload?: BlockchainBalancePayload) => Promise<void>;
  /**
   * Forget every read in flight. Must run when a session ends: this map is app-scoped, so a
   * read that can never settle (its request belongs to a session that is gone) would
   * otherwise be handed to the next session's caller for that chain, which then never hydrates.
   */
  reset: () => void;
}

/**
 * Repopulates the store from the user's own database, so the view paints before any network query.
 *
 * @remarks
 * Deliberately not an activity: no task-centre row, cancel or progress. Do not give it one.
 *
 * Deduplicated by chain, so a second caller for a live chain joins the read in flight and its
 * parameters. Overlapping a network refresh is safe because `processBalanceResult` discards a
 * payload older than what the chain already holds, whichever order they land in.
 */
export const useBalanceHydration = createSharedComposable((): UseBalanceHydrationReturn => {
  const { supportedChains } = useSupportedChains();
  const { clearChainBalances, handleCachedFetch, shouldQuery } = useBalanceProcessingService();
  const { prices } = storeToRefs(useBalancePricesStore());
  const { updatePrices } = useBalancesStore();
  const { startHydration, stopHydration } = useBalanceRefreshState();
  const valueThreshold = useValueThreshold(BalanceSource.BLOCKCHAIN);

  /** The read in flight per chain — the subject dedup. Entries exist only while a read is live. */
  const inflight = new Map<string, Promise<void>>();

  /**
   * Bumped by {@link reset}, so a read started before a session ended can tell that it has been
   * abandoned. Clearing the map is not enough on its own: the abandoned read still settles later
   * and still runs its own teardown, which would then act on the *next* session's state.
   */
  let generation = 0;

  const readChain = async (payload: BlockchainBalancePayload, chain: string, era: number): Promise<void> => {
    const chainPayload = { addresses: payload.addresses, blockchain: chain, isXpub: payload.isXpub ?? false };
    const threshold = get(valueThreshold);

    /**
     * One attempt, with its outcome placed in the channel `retry` reads.
     *
     * `retry` takes no predicate — it retries anything in the `err` channel. A read that was
     * cancelled (a logout mid-walk, a request the queue dropped) must settle where it is rather
     * than be tried twice more against a session that is gone, so only an *actionable* failure
     * goes in `err`; everything else short-circuits as `ok`.
     */
    const readOnce = async (): ResultAsync<Result<void, TaskError>, TaskError> => {
      const outcome = await handleCachedFetch(chainPayload, threshold);
      return isErr(outcome) && isActionable(outcome.error) ? err(outcome.error) : ok(outcome);
    };

    startHydration(chain);
    try {
      await retry(readOnce, HYDRATION_RETRY);
    }
    finally {
      if (era === generation)
        stopHydration(chain);
    }
  };

  const hydrateChain = async (payload: BlockchainBalancePayload, chain: string): Promise<void> => {
    if (!shouldQuery(chain)) {
      clearChainBalances(chain);
      return;
    }

    const running = inflight.get(chain);
    if (running)
      return running;

    const era = generation;
    const read = readChain(payload, chain, era).finally(() => {
      if (inflight.get(chain) === read)
        inflight.delete(chain);
    });
    inflight.set(chain, read);
    return read;
  };

  const hydrate = async (payload: BlockchainBalancePayload = {}): Promise<void> => {
    const { blockchain } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);

    /**
     * `allWithConcurrency` **short-circuits on the first `err`**: in-flight factories finish and
     * no new ones start. One chain's read failing must not abandon the rest, so every factory is
     * infallible — `ResultAsync<void, never>`. Nothing in the package enforces that, and the naive
     * call site silently drops chains while looking entirely correct.
     */
    const factories = chains.map(chain => async (): ResultAsync<void, never> => {
      try {
        await hydrateChain(payload, chain);
      }
      catch (error: unknown) {
        // A rejection here is a rejection of the whole batch, so it never leaves this factory.
        // `handleCachedFetch` reports what it owns; this covers a throw on the way to it.
        logger.error(error);
      }
      return ok(undefined);
    });

    await allWithConcurrency(factories, HYDRATION_CONCURRENCY);
    updatePrices(get(prices));
  };

  const reset = (): void => {
    generation += 1;
    inflight.clear();
  };

  return { hydrate, reset };
});
