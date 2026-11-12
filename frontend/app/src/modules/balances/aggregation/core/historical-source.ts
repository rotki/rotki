import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { type BigNumber, Zero } from '@rotki/common';
import { addBalanceEntry, type BalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';
import { TRADE_LOCATION_BANKS } from '@/modules/core/common/defaults';

/** The protocol key under which an account's own holdings are reported, matching `fromBlockchain`. */
const ADDRESS_PROTOCOL = 'address';

/**
 * The lookups a history-derived entry needs to become a priced balance source.
 *
 * @remarks
 * `matchChain` resolves a bucket's location (such as `ethereum`) to its canonical chain id (`eth`);
 * a bucket whose location does not resolve to a chain is an exchange, bank or manual location.
 */
export interface HistoricalSourceContext extends Pick<AggregationContext, 'priceOf' | 'resolveIdentifier'> {
  readonly matchChain: (location: string) => string | undefined;
}

/** Values a history entry at current prices, or zero when the asset has no price yet. */
function pricedBalance(entry: HistoricalBalanceEntry, price: BigNumber): BalanceEntry {
  const value = price.gt(0) ? entry.amount.multipliedBy(price) : Zero;
  return { amount: entry.amount, value };
}

/**
 * The current history-derived buckets every history surface shows.
 *
 * @remarks
 * Two buckets are left out. A `banks` bucket, because the history view carries bank balances
 * through from the live side and counting the bucket too would count them twice. And, when
 * `valueThreshold` is set, a chain-location bucket worth no more than it, matching the live
 * blockchain small-balance filter. Filtering here, once, keeps the headline, legend, tiles and
 * breakdowns summing to the same total.
 *
 * @param entries - the current buckets from `POST /balances/historical/current`
 * @param context - pricing, identifier and chain lookups
 * @param valueThreshold - the blockchain small-balance threshold, if the setting is active
 */
export function visibleHistoricalEntries(
  entries: readonly HistoricalBalanceEntry[],
  context: HistoricalSourceContext,
  valueThreshold: BigNumber | undefined,
): HistoricalBalanceEntry[] {
  return entries.filter((entry) => {
    if (entry.location === TRADE_LOCATION_BANKS)
      return false;
    if (valueThreshold === undefined || context.matchChain(entry.location) === undefined)
      return true;
    return pricedBalance(entry, context.priceOf(context.resolveIdentifier(entry.asset))).value.gt(valueThreshold);
  });
}

/**
 * Normalises current history-derived buckets into a source for `summarizeBalances`.
 *
 * @remarks
 * Wallet buckets (no protocol, a chain location) become the `address` protocol with a per-chain
 * split, matching `fromBlockchain`. Protocol buckets keep their counterparty as the key, and every
 * other location (exchange, external) is keyed by its location. Values are computed at the
 * resolved identifier's current price. Filtering is {@link visibleHistoricalEntries}'s job.
 *
 * @param entries - the buckets to normalise
 * @param context - pricing, identifier and chain lookups
 */
export function fromHistoricalEntries(
  entries: readonly HistoricalBalanceEntry[],
  context: HistoricalSourceContext,
): AssetBalanceEntries {
  const result: AssetBalanceEntries = {};

  for (const entry of entries) {
    const chain = context.matchChain(entry.location);
    const balance = pricedBalance(entry, context.priceOf(context.resolveIdentifier(entry.asset)));

    let protocol: string;
    let balanceEntry: BalanceEntry;
    if (entry.protocol != null) {
      protocol = entry.protocol;
      balanceEntry = balance;
    }
    else if (chain !== undefined) {
      protocol = ADDRESS_PROTOCOL;
      balanceEntry = { ...balance, chains: { [chain]: balance } };
    }
    else {
      protocol = entry.location;
      balanceEntry = balance;
    }

    addBalanceEntry(result[entry.asset] ??= {}, protocol, balanceEntry);
  }

  return result;
}
