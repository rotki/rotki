import type { NonEmptyArray } from 'plainfp/non-empty-array';
import type { Result } from 'plainfp/result';
import { tag } from 'plainfp/tagged';

/** A place balances are refreshed from, plus the pricing pass that values them. */
export const RefreshSource = {
  BANKS: 'banks',
  BLOCKCHAIN: 'blockchain',
  EXCHANGES: 'exchanges',
  MANUAL: 'manual',
  PRICES: 'prices',
} as const;

export type RefreshSource = (typeof RefreshSource)[keyof typeof RefreshSource];

/** A source that holds balances; pricing only values them. */
export type BalanceSource = Exclude<RefreshSource, typeof RefreshSource.PRICES>;

/** A refresh step that threw or rejected instead of settling. */
export const RefreshFailed = tag('RefreshFailed');

export type RefreshFailure = ReturnType<typeof RefreshFailed<{ source: RefreshSource; cause: unknown }>>;

/** Every step that failed, in the order the steps were declared. Absent when all succeeded. */
export type RefreshOutcome = Result<void, NonEmptyArray<RefreshFailure>>;

/**
 * What the refresher needs from the app, as plain functions.
 *
 * @remarks
 * Each action resolves once its work settles. The stores behind them report their own errors to
 * the user, so a port only rejects on something unexpected; the refresher turns that into a
 * {@link RefreshFailure} instead of letting it escape.
 */
export interface BalanceRefreshPorts {
  /** Every chain the user can hold balances on. */
  readonly supportedChains: () => readonly string[];
  /** Whether token detection covers the chain; the others can only be queried. */
  readonly supportsDetection: (chain: string) => boolean;
  /** The user's choice of what a blockchain refresh does when the caller does not say. */
  readonly redetectByDefault: () => boolean;
  readonly queryChains: (chains: readonly string[]) => Promise<void>;
  /** Detects tokens and writes the balances it finds, which makes it a refresh for those chains. */
  readonly detectTokens: (chains: readonly string[]) => Promise<void>;
  readonly queryExchanges: () => Promise<void>;
  readonly queryBanks: () => Promise<void>;
  /** Re-reads the manual balances the user entered; they come from the local database, not a network. */
  readonly queryManual: () => Promise<void>;
  readonly refreshPrices: () => Promise<void>;
}

export interface BlockchainRefreshOptions {
  /** Chains to refresh; every supported chain when absent. */
  readonly chains?: readonly string[];
  /** Detect tokens instead of querying, where detection is supported; the user's default when absent. */
  readonly redetect?: boolean;
}

export interface BalanceRefresher {
  readonly refreshBlockchain: (options?: BlockchainRefreshOptions) => Promise<RefreshOutcome>;
  /** Every source, then prices once all of them have settled. */
  readonly refreshAll: (options?: Pick<BlockchainRefreshOptions, 'redetect'>) => Promise<RefreshOutcome>;
  /** One source, then prices once it has settled. */
  readonly refreshSource: (source: BalanceSource, options?: Pick<BlockchainRefreshOptions, 'redetect'>) => Promise<RefreshOutcome>;
  readonly refreshPrices: () => Promise<RefreshOutcome>;
}
