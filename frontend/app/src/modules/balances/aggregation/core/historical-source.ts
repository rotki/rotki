import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { type BigNumber, Zero } from '@rotki/common';
import { addBalanceEntry, type BalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';

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
 * Normalises current history-derived buckets into a source for `summarizeBalances`.
 *
 * @remarks
 * Wallet buckets (no protocol, a chain location) become the `address` protocol with a per-chain
 * split, matching `fromBlockchain`. Protocol buckets keep their counterparty as the key, and every
 * other location (exchange, bank, external) is keyed by its location. Values are computed at the
 * resolved identifier's current price. When `valueThreshold` is set, chain-location buckets worth
 * no more than it are dropped, matching the queried blockchain small-balance filter.
 *
 * @param entries - the current buckets from `POST /balances/historical/current`
 * @param context - pricing, identifier and chain lookups
 * @param valueThreshold - the blockchain small-balance threshold, if the setting is active
 */
export function fromHistoricalEntries(
  entries: readonly HistoricalBalanceEntry[],
  context: HistoricalSourceContext,
  valueThreshold: BigNumber | undefined,
): AssetBalanceEntries {
  const result: AssetBalanceEntries = {};

  for (const entry of entries) {
    const chain = context.matchChain(entry.location);
    const balance = pricedBalance(entry, context.priceOf(context.resolveIdentifier(entry.asset)));

    if (chain !== undefined && valueThreshold !== undefined && !balance.value.gt(valueThreshold))
      continue;

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
