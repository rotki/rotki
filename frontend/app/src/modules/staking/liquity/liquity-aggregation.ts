import type {
  AssetBalance,
  Balance,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatisticDetails,
  LiquityStatistics,
} from '@rotki/common';
import { zeroBalance } from '@/modules/core/common/data/bignumbers';
import { balanceSum } from '@/modules/core/common/data/calculation';
import { uniqueStrings } from '@/modules/core/common/data/data';

/** A position held directly, through DS proxies, or both. Staking and pool details share it. */
interface DetailWithProxies<T> {
  balances: T | null;
  proxies: Record<string, T> | null;
}

/** A fixed set of named asset balances: staked/rewards, or deposited/gains/rewards. */
type BalanceEntry = Record<string, AssetBalance>;

/**
 * Every entry for the given addresses, own balances and proxies alike.
 *
 * @param selectedAddresses - an empty list means every address, as an absent account filter does
 */
function selectEntries<T extends BalanceEntry>(
  source: Record<string, DetailWithProxies<T>>,
  selectedAddresses: string[],
): T[] {
  const selected: T[] = [];

  for (const address in source) {
    if (selectedAddresses.length > 0 && !selectedAddresses.includes(address))
      continue;

    const detail = source[address];
    if (detail.balances)
      selected.push(detail.balances);

    if (detail.proxies)
      selected.push(...Object.values(detail.proxies));
  }

  return selected;
}

/**
 * Sums the selected entries field by field.
 *
 * @remarks
 * Each field keeps its asset identifier: `balanceSum` returns only an amount and a value, and every
 * entry names the same asset for a given field.
 *
 * @returns the summed entry, or `null` when nothing was selected
 */
export function aggregateEntries<T extends BalanceEntry>(
  source: Record<string, DetailWithProxies<T>>,
  selectedAddresses: string[],
): T | null {
  return selectEntries(source, selectedAddresses).reduce<T | null>((total, entry) => {
    // This copy is what keeps the store's objects intact; later fields are reassigned, not mutated.
    if (total === null)
      return { ...entry };

    for (const key in total)
      total[key] = { ...total[key], ...balanceSum(total[key], entry[key]) };

    return total;
  }, null);
}

/**
 * The proxies each selected address holds a position through, across staking and pools.
 *
 * @param selectedAddresses - only these count; with no account filter there is no owner to
 * attribute a proxy to, so nothing is reported
 * @returns the proxies by owner, or `null` when there are none
 */
export function collectProxies(
  staking: LiquityStakingDetails,
  pools: LiquityPoolDetails,
  selectedAddresses: string[],
): Record<string, string[]> | null {
  const proxies: Record<string, string[]> = {};

  const add = (owner: string, addresses: string[]): void => {
    proxies[owner] = proxies[owner] === undefined
      ? addresses
      : [...proxies[owner], ...addresses].filter(uniqueStrings);
  };

  for (const address of selectedAddresses) {
    for (const source of [pools[address], staking[address]]) {
      const owned = Object.keys(source?.proxies ?? {});
      if (owned.length > 0)
        add(address, owned);
    }
  }

  return Object.keys(proxies).length === 0 ? null : proxies;
}

/** Sums two lists of asset balances into one entry per asset. */
export function mergeAssetBalances(first: AssetBalance[], second: AssetBalance[]): AssetBalance[] {
  const combined = [...first, ...second];

  return combined
    .map(({ asset }) => asset)
    .filter(uniqueStrings)
    .map(asset => ({
      asset,
      ...combined
        .filter(item => item.asset === asset)
        .reduce<Balance>((previous, current) => balanceSum(previous, current), zeroBalance()),
    }));
}

/**
 * The statistics to display.
 *
 * @remarks
 * With no account filter this is the global figure the backend already aggregated; with one it is
 * the selected addresses summed together.
 *
 * @returns the statistics, or `null` when neither is available
 */
export function aggregateStatistics(
  statistics: LiquityStatistics | null,
  selectedAddresses: string[],
): LiquityStatisticDetails | null {
  if (!statistics)
    return null;

  if (selectedAddresses.length === 0)
    return statistics.globalStats ?? null;

  const byAddress = statistics.byAddress;
  if (!byAddress)
    return null;

  let total: LiquityStatisticDetails | null = null;

  for (const address in byAddress) {
    if (!selectedAddresses.includes(address))
      continue;

    const statistic = byAddress[address];
    if (total === null) {
      total = { ...statistic };
      continue;
    }

    const { stabilityPoolGains, stakingGains, ...totals } = statistic;

    let key: keyof typeof totals;
    for (key in totals)
      total[key] = total[key].plus(totals[key]);

    total.stakingGains = mergeAssetBalances(total.stakingGains, stakingGains);
    total.stabilityPoolGains = mergeAssetBalances(total.stabilityPoolGains, stabilityPoolGains);
  }

  return total;
}

/** Every address holding a liquity position, whether staked, pooled, or both. */
export function collectAvailableAddresses(
  staking: LiquityStakingDetails,
  pools: LiquityPoolDetails,
): string[] {
  return [...Object.keys(staking), ...Object.keys(pools)].filter(uniqueStrings);
}
