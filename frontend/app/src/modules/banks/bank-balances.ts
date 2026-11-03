import type { FormatOptions } from '@/modules/assets/amount-display/types';
import type { AssetBalances } from '@/modules/balances/types/balances';
import type { BankConnectionBalances, BankConnectionIdentity } from '@/modules/banks/types';
import { zeroBalance } from '@/modules/core/common/data/bignumbers';
import { balanceSum } from '@/modules/core/common/data/calculation';

/** Bank balances are kept in cents, so every bank amount shows exactly two decimals. */
export const BANK_AMOUNT_FORMAT: FormatOptions = { decimals: 2 };

function sameConnection(a: BankConnectionIdentity, b: BankConnectionIdentity): boolean {
  return a.connector === b.connector && a.name === b.name;
}

/**
 * The stored connection balances with the freshly queried ones in their place.
 *
 * @remarks
 * A query for one connection returns only that connection, so the others are kept as they were. A
 * connection queried for the first time is appended.
 */
export function mergeConnectionBalances(
  current: readonly BankConnectionBalances[],
  fresh: readonly BankConnectionBalances[],
): BankConnectionBalances[] {
  const kept = current.filter(entry => !fresh.some(update => sameConnection(entry, update)));
  return [...kept, ...fresh];
}

/** What all the given connections hold together, per asset. */
export function aggregateConnectionBalances(connections: readonly BankConnectionBalances[]): AssetBalances {
  const aggregate: AssetBalances = {};
  for (const { balances } of connections) {
    for (const [asset, balance] of Object.entries(balances))
      aggregate[asset] = balanceSum(aggregate[asset] ?? zeroBalance(), balance);
  }
  return aggregate;
}
