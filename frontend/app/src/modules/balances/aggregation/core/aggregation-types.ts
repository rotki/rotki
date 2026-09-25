import type { BigNumber } from '@rotki/common';
import type { BalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';

/** One asset's balances, keyed by protocol or location. */
export type ProtocolBalanceEntries = Record<string, BalanceEntry>;

/** Balances keyed by asset, then by protocol or location: the shape every source is normalised to. */
export type AssetBalanceEntries = Record<string, ProtocolBalanceEntries>;

/**
 * What the aggregation needs from the rest of the app, passed in by the adapter that owns the stores.
 *
 * @remarks
 * Every member must be a plain lookup. `collectionOf` may start a background fetch the first time it
 * sees an asset, but must answer synchronously from what is already known.
 */
export interface AggregationContext {
  /** Maps an identifier to the one it is treated as, such as `ETH2` to `ETH` when they are merged. */
  readonly resolveIdentifier: (identifier: string) => string;
  readonly isAssetIgnored: (identifier: string) => boolean;
  /** The asset's price, or the no-price sentinel when none is known yet. */
  readonly priceOf: (asset: string) => BigNumber;
  /** The collection an asset belongs to, if any. */
  readonly collectionOf: (asset: string) => string | undefined;
  /** The asset that heads a collection, if known. */
  readonly mainAssetOf: (collectionId: string) => string | undefined;
}

export interface SummaryOptions {
  /** Leave ignored assets out. Defaults to true. */
  readonly hideIgnored?: boolean;
  /** Fold the members of a collection into one row. Defaults to true. */
  readonly groupCollections?: boolean;
}
