import { cloneDeep } from 'lodash-es';
import type { Blockchain } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AccountAssetBalances, AssetBalances } from '@/types/balances';
import type { Balances, BlockchainAssetBalances, BtcBalances } from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';

export function updateTotalsPrices(
  state: MaybeRef<Record<string, AssetBalances>>,
  prices: MaybeRef<AssetPrices>,
): Record<string, AssetBalances> {
  const totals = cloneDeep(get(state));

  for (const chain in totals) {
    const balances = totals[chain];
    for (const asset in balances) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice)
        continue;

      const amount = balances[asset].amount;
      balances[asset] = {
        amount,
        usdValue: amount.times(assetPrice.value),
      };
    }
  }
  return totals;
}

export function updateBalancesPrices(balances: Balances, prices: MaybeRef<AssetPrices>): Balances {
  for (const asset in balances) {
    const assetPrice = get(prices)[asset];
    if (!assetPrice)
      continue;

    const assetInfo = balances[asset];
    balances[asset] = {
      amount: assetInfo.amount,
      usdValue: assetInfo.amount.times(assetPrice.value),
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

export function updateAssetBalances(
  balances: MaybeRef<AccountAssetBalances>,
  prices: MaybeRef<AssetPrices>,
): AccountAssetBalances {
  const state = cloneDeep(get(balances));
  for (const address in state) {
    const addressAssets = state[address];
    for (const asset in addressAssets) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice)
        continue;

      const amount = addressAssets[asset].amount;
      addressAssets[asset] = {
        amount,
        usdValue: amount.times(assetPrice.value),
      };
    }
  }
  return state;
}

export function updateBtcPrices(
  state: MaybeRef<Record<typeof Blockchain.BTC | typeof Blockchain.BCH, BtcBalances>>,
  prices: MaybeRef<AssetPrices>,
): Record<typeof Blockchain.BTC | typeof Blockchain.BCH, BtcBalances> {
  const balances = cloneDeep(get(state));

  for (const [chain, balance] of Object.entries(balances)) {
    const assetPrice = get(prices)[chain];
    if (!assetPrice)
      continue;

    for (const address in balance.standalone) {
      const addressBalance = balance.standalone[address];
      const amount = addressBalance.amount;
      balance.standalone[address] = {
        amount,
        usdValue: amount.times(assetPrice.value),
      };
    }
    const xpubs = balance.xpubs;
    if (xpubs) {
      for (const xpub of xpubs) {
        for (const address in xpub.addresses) {
          const balance = xpub.addresses[address];
          const amount = balance.amount;
          xpub.addresses[address] = {
            amount,
            usdValue: amount.times(assetPrice.value),
          };
        }
      }
    }
  }

  return balances;
}
