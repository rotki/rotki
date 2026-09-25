import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { LocationBalance } from '@/modules/balances/types/balances';
import { type BigNumber, Zero } from '@rotki/common';
import { assetSum } from '@/modules/core/common/data/calculation';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';

/**
 * Everything held on-chain across the given chains, in the main currency, with ignored assets left out.
 *
 * @remarks
 * An account whose balances arrived without an `assets` map contributes nothing rather than failing.
 */
export function blockchainValue(balances: Balances, isAssetIgnored: (identifier: string) => boolean): BigNumber {
  let total = Zero;
  for (const accounts of Object.values(balances)) {
    for (const { assets } of Object.values(accounts)) {
      if (assets)
        total = total.plus(assetSum(assets, isAssetIgnored));
    }
  }
  return total;
}

function addTo(totals: Record<string, BigNumber>, location: string, value: BigNumber): void {
  totals[location] = totals[location]?.plus(value) ?? value;
}

/**
 * Value per trade location, with every chain folded into the umbrella `blockchain` location.
 *
 * @param blockchain - the on-chain total, from {@link blockchainValue}
 * @param exchanges - each exchange's total, ignored assets already left out
 * @param manual - each manual location's total
 */
export function totalsByLocation(
  blockchain: BigNumber,
  exchanges: readonly { location: string; total: BigNumber }[],
  manual: readonly LocationBalance[],
): Record<string, BigNumber> {
  const totals: Record<string, BigNumber> = { [TRADE_LOCATION_BLOCKCHAIN]: blockchain };
  for (const { location, total } of exchanges)
    addTo(totals, location, total);
  for (const { location, value } of manual)
    addTo(totals, location, value);
  return totals;
}

/**
 * On-chain value per chain, keyed by the trade location that stands for the chain, such as
 * `ethereum` for `eth`. Chains holding nothing are left out.
 */
export function totalsByChainLocation(
  balances: Balances,
  locations: readonly string[],
  matchChain: (location: string) => string | undefined,
  isAssetIgnored: (identifier: string) => boolean,
): Record<string, BigNumber> {
  const totals: Record<string, BigNumber> = {};
  for (const location of locations) {
    const chain = matchChain(location);
    if (!chain || !balances[chain])
      continue;

    const total = blockchainValue({ [chain]: balances[chain] }, isAssetIgnored);
    if (!total.isZero())
      totals[location] = total;
  }
  return totals;
}
