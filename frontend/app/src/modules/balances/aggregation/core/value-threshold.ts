import type { BigNumber } from '@rotki/common';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AssetProtocolBalances, BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';

function assetsAbove(balances: AssetProtocolBalances, threshold: BigNumber): AssetProtocolBalances {
  const result: AssetProtocolBalances = {};
  for (const [asset, protocols] of Object.entries(balances)) {
    const kept = Object.entries(protocols).filter(([, balance]) => balance.value.gt(threshold));
    if (kept.length > 0)
      result[asset] = Object.fromEntries(kept);
  }
  return result;
}

/**
 * The blockchain balances worth more than the threshold, by the value each balance holds.
 *
 * @remarks
 * Filtered here rather than by the backend because a cached read there values a balance from
 * historical prices, which are usually missing, so it would drop balances of any size. The values
 * here follow the latest prices. A balance with no price yet is worth zero and stays hidden until
 * one lands, so whatever fetches prices must read the unfiltered balances, or it never would.
 *
 * An account left with nothing is dropped, and a chain left with no accounts stays as an empty entry.
 */
export function balancesAboveThreshold(balances: Balances, threshold: BigNumber): Balances {
  const result: Balances = {};
  for (const [chain, accounts] of Object.entries(balances)) {
    const kept: BlockchainAssetBalances = {};
    for (const [address, { assets, liabilities }] of Object.entries(accounts)) {
      const keptAssets = assetsAbove(assets, threshold);
      const keptLiabilities = assetsAbove(liabilities, threshold);
      if (Object.keys(keptAssets).length > 0 || Object.keys(keptLiabilities).length > 0)
        kept[address] = { assets: keptAssets, liabilities: keptLiabilities };
    }
    result[chain] = kept;
  }
  return result;
}
