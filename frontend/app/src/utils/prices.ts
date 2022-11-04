import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import cloneDeep from 'lodash/cloneDeep';
import { AccountAssetBalances, AssetBalances } from '@/types/balances';
import {
  Balances,
  BlockchainAssetBalances,
  BtcBalances
} from '@/types/blockchain/balances';
import { AssetPrices } from '@/types/prices';

export const updateTotalsPrices = <T extends Blockchain>(
  state: MaybeRef<Record<T, AssetBalances>>,
  prices: MaybeRef<AssetPrices>
): Record<T, AssetBalances> => {
  const totals = cloneDeep(get(state));

  for (const chain in totals) {
    const balances = totals[chain as T] as AssetBalances;
    for (const asset in balances) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice) {
        continue;
      }

      const amount = balances[asset].amount;
      balances[asset] = {
        amount,
        usdValue: amount.times(assetPrice.usdPrice ?? assetPrice.value)
      };
    }
  }
  return totals;
};

export const updateBalancesPrices = (
  balances: Balances,
  prices: MaybeRef<AssetPrices>
): Balances => {
  for (const asset in balances) {
    const assetPrice = get(prices)[asset];
    if (!assetPrice) {
      continue;
    }
    const assetInfo = balances[asset];
    balances[asset] = {
      amount: assetInfo.amount,
      usdValue: assetInfo.amount.times(assetPrice.usdPrice ?? assetPrice.value)
    };
  }
  return balances;
};

export const updateBlockchainAssetBalances = <T extends Blockchain>(
  balances: MaybeRef<Record<T, BlockchainAssetBalances>>,
  prices: MaybeRef<AssetPrices>
): Record<T, BlockchainAssetBalances> => {
  const state = cloneDeep(get(balances));
  for (const chain in state) {
    const balances = state[chain as T] as BlockchainAssetBalances;
    for (const address in balances) {
      const { assets, liabilities } = balances[address];
      balances[address] = {
        assets: updateBalancesPrices(assets, prices),
        liabilities: updateBalancesPrices(liabilities, prices)
      };
    }
  }
  return state;
};

export const updateAssetBalances = (
  balances: MaybeRef<AccountAssetBalances>,
  prices: MaybeRef<AssetPrices>
): AccountAssetBalances => {
  const state = cloneDeep(get(balances));
  for (const address in state) {
    const addressAssets = state[address];
    for (const asset in addressAssets) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice) {
        continue;
      }
      const amount = addressAssets[asset].amount;
      addressAssets[asset] = {
        amount,
        usdValue: amount.times(assetPrice.usdPrice ?? assetPrice.value)
      };
    }
  }
  return state;
};

export const updateBtcPrices = (
  state: MaybeRef<
    Record<typeof Blockchain.BTC | typeof Blockchain.BCH, BtcBalances>
  >,
  prices: MaybeRef<AssetPrices>
): Record<typeof Blockchain.BTC | typeof Blockchain.BCH, BtcBalances> => {
  const balances = cloneDeep(get(state));

  for (const [chain, balance] of Object.entries(balances)) {
    const assetPrice = get(prices)[chain];
    if (!assetPrice) {
      continue;
    }

    for (const address in balance.standalone) {
      const addressBalance = balance.standalone[address];
      const amount = addressBalance.amount;
      balance.standalone[address] = {
        amount,
        usdValue: amount.times(assetPrice.usdPrice ?? assetPrice.value)
      };
    }
    const xpubs = balance.xpubs;
    if (xpubs) {
      for (let i = 0; i < xpubs.length; i++) {
        const xpub = xpubs[i];
        for (const address in xpub.addresses) {
          const balance = xpub.addresses[address];
          const amount = balance.amount;
          xpub.addresses[address] = {
            amount: amount,
            usdValue: amount.times(assetPrice.usdPrice ?? assetPrice.value)
          };
        }
      }
    }
  }

  return balances;
};
