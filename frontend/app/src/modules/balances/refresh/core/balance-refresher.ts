import { pipe } from 'plainfp';
import { filter, flatMap as flatMapArray, map as mapArray } from 'plainfp/arrays';
import { fromArray, type NonEmptyArray, of } from 'plainfp/non-empty-array';
import { match as matchOption } from 'plainfp/option';
import { err, match as matchResult, ok } from 'plainfp/result';
import { flatMap, fromAsync, mapError, type ResultAsync } from 'plainfp/result-async';
import { type BlockchainRefreshPlan, planBlockchainRefresh } from './blockchain-refresh-plan';
import {
  type BalanceRefresher,
  type BalanceRefreshPorts,
  type BalanceSource,
  type BlockchainRefreshOptions,
  RefreshFailed,
  type RefreshFailure,
  type RefreshOutcome,
  RefreshSource,
} from './refresh-types';

type Attempt<T> = ResultAsync<T, NonEmptyArray<RefreshFailure>>;

/** Runs one step, turning a throw or a rejection into a failure named after its source. */
async function attempt<T>(source: RefreshSource, run: () => Promise<T>): Attempt<T> {
  return pipe(
    fromAsync(run, cause => RefreshFailed({ cause, source })),
    mapError(failure => of(failure)),
  );
}

/**
 * Folds outcomes into one, keeping every failure in order.
 *
 * @remarks
 * `all` from `plainfp/result-async` stops at the first error, which would hide the sources that
 * failed after it, so the failures are gathered here instead.
 */
function combine(outcomes: readonly RefreshOutcome[]): RefreshOutcome {
  return pipe(
    outcomes,
    flatMapArray(outcome => matchResult(outcome, {
      err: (failures): readonly RefreshFailure[] => failures,
      ok: () => [],
    })),
    fromArray,
    matchOption({
      none: (): RefreshOutcome => ok(undefined),
      some: failures => err(failures),
    }),
  );
}

/** Runs the steps concurrently and resolves once all of them have settled. */
async function settle(steps: readonly Promise<RefreshOutcome>[]): Promise<RefreshOutcome> {
  return combine(await Promise.all(steps));
}

/**
 * Refreshes balances from every source through the given ports.
 *
 * @remarks
 * No method rejects: every failure comes back in the outcome, so a failing source can never stop
 * the steps after it. {@link BalanceRefresher.refreshAll} prices only once every source settled,
 * so the new balances are the ones valued, and it prices even when a source failed.
 */
export function createBalanceRefresher(ports: BalanceRefreshPorts): BalanceRefresher {
  async function runPlan({ detect, query }: BlockchainRefreshPlan): Promise<RefreshOutcome> {
    return pipe(
      [
        { chains: detect, run: ports.detectTokens },
        { chains: query, run: ports.queryChains },
      ],
      filter(step => step.chains.length > 0),
      mapArray(async step => attempt(RefreshSource.BLOCKCHAIN, async () => step.run(step.chains))),
      settle,
    );
  }

  async function refreshBlockchain({ chains, redetect }: BlockchainRefreshOptions = {}): Promise<RefreshOutcome> {
    return pipe(
      attempt(RefreshSource.BLOCKCHAIN, async () => planBlockchainRefresh({
        chains: chains ?? ports.supportedChains(),
        redetect: redetect ?? ports.redetectByDefault(),
        supportsDetection: ports.supportsDetection,
      })),
      flatMap(runPlan),
    );
  }

  async function refreshPrices(): Promise<RefreshOutcome> {
    return attempt(RefreshSource.PRICES, ports.refreshPrices);
  }

  async function querySource(source: BalanceSource, redetect?: boolean): Promise<RefreshOutcome> {
    switch (source) {
      case RefreshSource.BLOCKCHAIN:
        return refreshBlockchain({ redetect });
      case RefreshSource.EXCHANGES:
        return attempt(source, ports.queryExchanges);
      case RefreshSource.BANKS:
        return attempt(source, ports.queryBanks);
      case RefreshSource.MANUAL:
        return attempt(source, ports.queryManual);
    }
  }

  /** Waits for the sources, then prices, so the balances just fetched are the ones valued. */
  async function thenPrices(sources: Promise<RefreshOutcome>): Promise<RefreshOutcome> {
    return combine([await sources, await refreshPrices()]);
  }

  async function refreshAll({ redetect }: Pick<BlockchainRefreshOptions, 'redetect'> = {}): Promise<RefreshOutcome> {
    return thenPrices(settle([
      querySource(RefreshSource.BLOCKCHAIN, redetect),
      querySource(RefreshSource.EXCHANGES),
      querySource(RefreshSource.BANKS),
      querySource(RefreshSource.MANUAL),
    ]));
  }

  async function refreshSource(source: BalanceSource, { redetect }: Pick<BlockchainRefreshOptions, 'redetect'> = {}): Promise<RefreshOutcome> {
    return thenPrices(querySource(source, redetect));
  }

  return {
    refreshAll,
    refreshBlockchain,
    refreshPrices,
    refreshSource,
  };
}
