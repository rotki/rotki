import type { Balances, BlockchainAssetBalances } from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import { cloneDeep } from 'es-toolkit';

export function updateBalancesPrices(balances: Balances, prices: MaybeRef<AssetPrices>): Balances {
  for (const asset in balances) {
    const assetPrice = get(prices)[asset];
    if (!assetPrice)
      continue;

    const assetInfo = balances[asset];
    balances[asset] = {
      amount: assetInfo.amount,
      usdValue: assetInfo.amount.times(assetPrice.usdPrice ?? assetPrice.value),
    };
  }
  return balances;
}

export function updateBlockchainAssetBalances(
  balances: MaybeRef<Record<string, BlockchainAssetBalances>>,
  prices: MaybeRef<AssetPrices>,
): Record<string, BlockchainAssetBalances> {
  const state = cloneDeep(get(balances));
  for (const chain in state) {
    const balances = state[chain];
    for (const address in balances) {
      const { assets, liabilities } = balances[address];
      balances[address] = {
        assets: updateBalancesPrices(assets, prices),
        liabilities: updateBalancesPrices(liabilities, prices),
      };
    }
  }
  return state;
}
