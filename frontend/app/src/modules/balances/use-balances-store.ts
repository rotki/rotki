import type { Balances } from '@/types/blockchain/accounts';
import type { BlockchainAssetBalances, BlockchainBalances } from '@/types/blockchain/balances';
import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import { updateBalancesPrices, updateBlockchainAssetBalances } from '@/utils/prices';
import { type BigNumber, Zero } from '@rotki/common';
import { camelCase } from 'es-toolkit';

function updatePriceData(data: ManualBalanceWithValue[], prices: MaybeRef<AssetPrices>): ManualBalanceWithValue[] {
  return data.map((item) => {
    const assetPrice = get(prices)[item.asset];
    if (!assetPrice)
      return item;

    return {
      ...item,
      usdValue: item.amount.times(assetPrice.usdPrice ?? assetPrice.value),
    };
  });
}

export const useBalancesStore = defineStore('balances', () => {
  const manualBalances = ref<ManualBalanceWithValue[]>([]);
  const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

  const exchangeBalances = ref<ExchangeData>({});
  const nonFungibleTotalValue = ref<BigNumber>(Zero);

  const blockchainBalances = ref<Balances>({});

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    set(blockchainBalances, updateBlockchainAssetBalances(blockchainBalances, prices));

    const exchanges = { ...get(exchangeBalances) };
    for (const exchange in exchanges) exchanges[exchange] = updateBalancesPrices(exchanges[exchange], prices);

    set(exchangeBalances, exchanges);

    set(manualBalances, updatePriceData(get(manualBalances), prices));
    set(manualLiabilities, updatePriceData(get(manualLiabilities), prices));
  };

  const updateBlockchainBalances = (chain: string, { perAccount }: BlockchainBalances): void => {
    const data = perAccount[camelCase(chain)] ?? {};
    set(blockchainBalances, {
      ...get(blockchainBalances),
      [chain]: data,
    });
  };

  const removeIgnoredAssets = (ignoredAssets: string[]): void => {
    const balances: Balances = { ...get(blockchainBalances) };

    for (const blockchain in balances) {
      const accounts: BlockchainAssetBalances = { ...balances[blockchain] };

      for (const account in accounts) {
        const balance = accounts[account];
        const assets = { ...balance.assets };
        const liabilities = { ...balance.liabilities };

        for (const asset of ignoredAssets) {
          delete assets[asset];
          delete liabilities[asset];
        }

        if (Object.keys(assets).length > 0 || Object.keys(liabilities).length > 0) {
          accounts[account] = {
            assets,
            liabilities,
          };
        }
        else {
          delete accounts[account];
        }
      }

      if (Object.keys(accounts).length === 0) {
        delete balances[blockchain];
      }
      else {
        balances[blockchain] = accounts;
      }
    }

    set(blockchainBalances, balances);
  };

  return {
    balances: blockchainBalances,
    exchangeBalances,
    manualBalances,
    manualLiabilities,
    nonFungibleTotalValue,
    removeIgnoredAssets,
    updateBalances: updateBlockchainBalances,
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancesStore, import.meta.hot));
