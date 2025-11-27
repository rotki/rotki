import type { MaybeRef } from '@vueuse/core';
import type { Balances } from '@/types/blockchain/accounts';
import type { BlockchainAssetBalances, BlockchainBalances } from '@/types/blockchain/balances';
import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import { type BigNumber, Zero } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { updateBlockchainAssetBalances, updateExchangeBalancesPrices, updateManualBalancePrices } from '@/utils/prices';

export const useBalancesStore = defineStore('balances', () => {
  const manualBalances = ref<ManualBalanceWithValue[]>([]);
  const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

  const exchangeBalances = ref<ExchangeData>({});
  const nonFungibleTotalValue = ref<BigNumber>(Zero);

  const blockchainBalances = ref<Balances>({});

  const { assetPriceInCurrentCurrency } = usePriceUtils();

  const getAssetPriceInCurrentCurrency = (asset: string): BigNumber | undefined => get(assetPriceInCurrentCurrency(asset));

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const latestPrices = get(prices);
    set(blockchainBalances, updateBlockchainAssetBalances(get(blockchainBalances), latestPrices, getAssetPriceInCurrentCurrency));

    const exchanges = { ...get(exchangeBalances) };
    for (const exchange in exchanges) exchanges[exchange] = updateExchangeBalancesPrices(exchanges[exchange], latestPrices, getAssetPriceInCurrentCurrency);

    set(exchangeBalances, exchanges);

    set(manualBalances, updateManualBalancePrices(get(manualBalances), latestPrices, assetPriceInCurrentCurrency));
    set(manualLiabilities, updateManualBalancePrices(get(manualLiabilities), latestPrices, assetPriceInCurrentCurrency));
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
