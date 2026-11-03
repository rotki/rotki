import type { FormatOptions } from '@/modules/assets/amount-display/types';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { BankConnectionBalances, BankConnectionIdentity } from '@/modules/banks/types';
import { zeroBalance } from '@/modules/core/common/data/bignumbers';
import { balanceSum } from '@/modules/core/common/data/calculation';
import { TRADE_LOCATION_BANKS } from '@/modules/core/common/defaults';

const USUAL_FORMAT: FormatOptions = {};
let amountFormats: Map<string, FormatOptions> | undefined;

/**
 * How a bank amount in `asset` shows: with exactly the decimals its currency uses.
 *
 * @remarks
 * A bank reports amounts in the currency's minor units, so EUR shows two decimals, JPY none and
 * KWD three. An asset that is not an ISO 4217 currency keeps the usual formatting; `Intl` alone
 * would format any three-letter code, `ETH` included, with two. One object per currency, so a
 * re-render passes the same format.
 */
export function bankAmountFormat(asset: string): FormatOptions {
  amountFormats ??= new Map(Intl.supportedValuesOf('currency').map(currency => [currency, {
    decimals: new Intl.NumberFormat('en', { currency, style: 'currency' }).resolvedOptions().maximumFractionDigits,
  }]));
  return amountFormats.get(asset) ?? USUAL_FORMAT;
}

/**
 * Every bank connection's balances summed under the one `banks` location, in the shape the
 * exchanges use, or nothing without a connection.
 *
 * @remarks
 * What the location-wide views read: the totals, the breakdown, a location page and the held
 * assets treat banks as one more location map. The bank pages read the connections themselves.
 */
export function bankLocationBalances(connections: readonly BankConnectionBalances[]): ExchangeData {
  if (connections.length === 0)
    return {};
  const banks: ExchangeData[string] = {};
  for (const { balances } of connections) {
    for (const [asset, balance] of Object.entries(balances))
      banks[asset] = balanceSum(banks[asset] ?? zeroBalance(), balance);
  }
  return { [TRADE_LOCATION_BANKS]: banks };
}

export function isSameConnection(a: BankConnectionIdentity, b: BankConnectionIdentity): boolean {
  return a.connector === b.connector && a.name === b.name;
}

/**
 * The stored connection balances with the freshly queried ones in their place.
 *
 * @remarks
 * A connection missing from `fresh` keeps its last known balances: a single-connection query
 * returns only that connection, and a full query leaves out a connection waiting on a TAN. A
 * removed connection is dropped when it is removed, not here.
 */
export function mergeConnectionBalances(
  current: readonly BankConnectionBalances[],
  fresh: readonly BankConnectionBalances[],
): BankConnectionBalances[] {
  const kept = current.filter(entry => !fresh.some(update => isSameConnection(entry, update)));
  return [...kept, ...fresh];
}
