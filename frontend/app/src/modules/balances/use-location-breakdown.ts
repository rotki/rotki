import type { BigNumber } from '@rotki/common';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AssetBalances } from '@/modules/balances/types/balances';
import type { ExchangeInfo } from '@/modules/balances/types/exchanges';
import { aggregateTotals } from '@/modules/accounts/account-helpers';

/**
 * Gets blockchain location breakdown
 */
export function getBlockchainLocationBreakdown(
  balances: Balances,
  resolveIdentifier: (id: string) => string,
  skipIdentifier: (asset: string) => boolean,
): AssetBalances {
  return aggregateTotals(balances, 'assets', {
    resolveIdentifier,
    skipIdentifier,
  });
}

/**
 * Gets exchange balances by location (values already in main currency)
 */
export function getExchangeByLocationBalances(
  exchanges: ExchangeInfo[],
): Record<string, BigNumber> {
  const balances: Record<string, BigNumber> = {};
  for (const { location, total } of exchanges) {
    const balance = balances[location];
    balances[location] = !balance ? total : total.plus(balance);
  }
  return balances;
}
