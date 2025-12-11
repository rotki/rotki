import type { Balance, BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { AssetBalances } from '@/types/balances';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
} from '@/types/blockchain/balances';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';

type AssetPriceGetter = (asset: string) => BigNumber | undefined;

export function updateBalancesPrices(
  balances: AssetProtocolBalances,
  prices: AssetPrices,
  getAssetPriceInCurrentCurrency?: AssetPriceGetter,
): AssetProtocolBalances {
  // Early return for empty objects
  const balanceKeys = Object.keys(balances);
  if (balanceKeys.length === 0)
    return {};

  const result: AssetProtocolBalances = {};

  for (const asset of balanceKeys) {
    const assetPrice = prices[asset];
    const protocols = balances[asset];

    if (!assetPrice) {
      result[asset] = protocols;
      continue;
    }

    const protocolKeys = Object.keys(protocols);
    if (protocolKeys.length === 0) {
      result[asset] = protocols;
      continue;
    }

    const protocolResult: typeof protocols = {};
    const currentCurrencyPrice = getAssetPriceInCurrentCurrency?.(asset);

    for (const protocol of protocolKeys) {
      const balance = protocols[protocol];
      const priceToUse = currentCurrencyPrice ?? assetPrice.value;
      const newBalance: Balance = {
        amount: balance.amount,
        value: priceToUse ? balance.amount.times(priceToUse) : balance.value,
      };
      protocolResult[protocol] = newBalance;
    }
    result[asset] = protocolResult;
  }
  return result;
}

export function updateExchangeBalancesPrices(
  balances: AssetBalances,
  prices: AssetPrices,
  getAssetPriceInCurrentCurrency?: AssetPriceGetter,
): AssetBalances {
  // Early return for empty objects
  const balanceKeys = Object.keys(balances);
  if (balanceKeys.length === 0)
    return {};

  const result: AssetBalances = {};

  for (const asset of balanceKeys) {
    const assetPrice = prices[asset];
    const assetInfo = balances[asset];

    if (!assetPrice) {
      result[asset] = assetInfo;
      continue;
    }

    const currentCurrencyPrice = getAssetPriceInCurrentCurrency?.(asset);
    const priceToUse = currentCurrencyPrice ?? assetPrice.value;
    result[asset] = {
      amount: assetInfo.amount,
      value: priceToUse ? assetInfo.amount.times(priceToUse) : assetInfo.value,
    };
  }
  return result;
}

export function updateBlockchainAssetBalances(
  balances: Record<string, BlockchainAssetBalances>,
  prices: AssetPrices,
  getAssetPriceInCurrentCurrency?: AssetPriceGetter,
): Record<string, BlockchainAssetBalances> {
  // Early return for empty objects
  const chainKeys = Object.keys(balances);
  if (chainKeys.length === 0)
    return {};

  const result: Record<string, BlockchainAssetBalances> = {};

  for (const chain of chainKeys) {
    const chainBalances = balances[chain];
    const addressKeys = Object.keys(chainBalances);

    if (addressKeys.length === 0) {
      result[chain] = chainBalances;
      continue;
    }

    const chainResult: BlockchainAssetBalances = {};

    for (const address of addressKeys) {
      const { assets, liabilities } = chainBalances[address];
      chainResult[address] = {
        assets: updateBalancesPrices(assets, prices, getAssetPriceInCurrentCurrency),
        liabilities: updateBalancesPrices(liabilities, prices, getAssetPriceInCurrentCurrency),
      };
    }
    result[chain] = chainResult;
  }
  return result;
}

export function updateManualBalancePrices(data: ManualBalanceWithValue[], prices: AssetPrices, assetPriceInCurrentCurrency: (asset: MaybeRef<string>) => ComputedRef<BigNumber>): ManualBalanceWithValue[] {
  return data.map((item) => {
    const assetPrice = prices[item.asset];
    if (!assetPrice)
      return item;

    return {
      ...item,
      value: item.amount.times(get(assetPriceInCurrentCurrency(item.asset))),
    };
  });
}
