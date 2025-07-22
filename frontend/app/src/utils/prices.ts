import type { AssetBalances } from '@/types/balances';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
} from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';

export function updateBalancesPrices(balances: AssetProtocolBalances, prices: AssetPrices): AssetProtocolBalances {
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
    const priceMultiplier = assetPrice.usdPrice ?? assetPrice.value;

    for (const protocol of protocolKeys) {
      const balance = protocols[protocol];
      protocolResult[protocol] = {
        amount: balance.amount,
        usdValue: balance.amount.times(priceMultiplier),
      };
    }
    result[asset] = protocolResult;
  }
  return result;
}

export function updateExchangeBalancesPrices(balances: AssetBalances, prices: AssetPrices): AssetBalances {
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

    result[asset] = {
      amount: assetInfo.amount,
      usdValue: assetInfo.amount.times(assetPrice.usdPrice ?? assetPrice.value),
    };
  }
  return result;
}

export function updateBlockchainAssetBalances(
  balances: Record<string, BlockchainAssetBalances>,
  prices: AssetPrices,
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
        assets: updateBalancesPrices(assets, prices),
        liabilities: updateBalancesPrices(liabilities, prices),
      };
    }
    result[chain] = chainResult;
  }
  return result;
}
