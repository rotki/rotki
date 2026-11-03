import type { BigNumber } from '@rotki/common';
import type { AssetPrices } from '@/modules/assets/prices/price-types';
import type { AssetBalances } from '@/modules/balances/types/balances';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
} from '@/modules/balances/types/blockchain-balances';
import type { BankConnectionBalances } from '@/modules/banks/types';

export function updateBalancesPrices(
  balances: AssetProtocolBalances,
  prices: AssetPrices,
): AssetProtocolBalances {
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

    for (const protocol of protocolKeys) {
      const balance = protocols[protocol];
      protocolResult[protocol] = {
        ...balance,
        value: assetPrice.value?.gt(0) ? balance.amount.times(assetPrice.value) : balance.value,
      };
    }
    result[asset] = protocolResult;
  }
  return result;
}

export function updateExchangeBalancesPrices(
  balances: AssetBalances,
  prices: AssetPrices,
): AssetBalances {
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
      value: assetPrice.value?.gt(0) ? assetInfo.amount.times(assetPrice.value) : assetInfo.value,
    };
  }
  return result;
}

export function updateBlockchainAssetBalances(
  balances: Record<string, BlockchainAssetBalances>,
  prices: AssetPrices,
): Record<string, BlockchainAssetBalances> {
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

/** Each item, such as a manual balance or a bank account, valued at the given prices; one whose asset has no positive price keeps its value. */
export function updateAssetValuePrices<T extends { asset: string; amount: BigNumber; value: BigNumber }>(data: readonly T[], prices: AssetPrices): T[] {
  return data.map((item) => {
    const assetPrice = prices[item.asset];
    if (!assetPrice)
      return item;

    return {
      ...item,
      value: assetPrice.value?.gt(0) ? item.amount.times(assetPrice.value) : item.value,
    };
  });
}

/** Each connection's balances and accounts valued at the given prices. */
export function updateBankBalancesPrices(connections: readonly BankConnectionBalances[], prices: AssetPrices): BankConnectionBalances[] {
  return connections.map(connection => ({
    ...connection,
    accounts: updateAssetValuePrices(connection.accounts, prices),
    balances: updateExchangeBalancesPrices(connection.balances, prices),
  }));
}
