import type { TradableAsset, TradableAssetWithoutValue } from '@/modules/onchain/types';
import type { MaybeRef } from '@vueuse/core';
import type BigNumber from 'bignumber.js';
import type { ComputedRef } from 'vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { sortDesc } from '@/utils/bignumbers';
import { One, Zero } from '@rotki/common';
import { useWalletStore } from './use-wallet-store';

interface UseTradableAssetReturn {
  allOwnedAssets: ComputedRef<TradableAsset[]>;
  getAssetDetail: (asset: MaybeRef<string>, chain: MaybeRef<string>) => ComputedRef<TradableAsset | undefined>;
}

export function useTradableAsset(address: MaybeRef<string | undefined>): UseTradableAssetReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { assetPrice, isAssetPriceInCurrentCurrency, useExchangeRate } = usePriceUtils();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { supportedChainsForConnectedAccount } = storeToRefs(useWalletStore());
  const { isEvm } = useSupportedChains();

  function priceInCurrentCurrency(asset: string): ComputedRef<BigNumber> {
    return computed<BigNumber>(() => {
      const currency = get(currencySymbol);
      if (asset === currency) {
        return One;
      }

      const price = get(assetPrice(asset)) || Zero;
      const isCurrentCurrency = get(isAssetPriceInCurrentCurrency(asset));
      if (isCurrentCurrency || currency === CURRENCY_USD) {
        return price;
      }

      const currentExchangeRate = get(useExchangeRate(currency));
      return price.multipliedBy(currentExchangeRate || One);
    });
  }

  const allOwnedAssets = computed<TradableAsset[]>(() => {
    const addressVal = get(address);
    const result: TradableAssetWithoutValue[] = [];

    // Iterate through each chain in balances
    Object.entries(get(balances)).forEach(([chain, chainBalances]) => {
      if (!get(isEvm(chain))) {
        return;
      }

      if (!get(supportedChainsForConnectedAccount).includes(chain)) {
        return;
      }

      if (addressVal) {
        // If address is provided, get balance for specific address
        const addressBalance = chainBalances[addressVal];
        if (addressBalance?.assets) {
          Object.entries(addressBalance.assets).forEach(([asset, balance]) => {
            if (balance.amount) {
              result.push({
                amount: balance.amount,
                asset,
                chain,
              });
            }
          });
        }
      }
      else {
        // If no address provided, aggregate balances from all addresses
        const assetsByChain = new Set<string>();
        Object.values(chainBalances).forEach((addressBalance) => {
          if (addressBalance?.assets) {
            Object.entries(addressBalance.assets).forEach(([asset, balance]) => {
              if (balance.amount) {
                const assetChainKey = `${asset}-${chain}`;
                if (!assetsByChain.has(assetChainKey)) {
                  assetsByChain.add(assetChainKey);
                  result.push({
                    amount: Zero,
                    asset,
                    chain,
                  });
                }
              }
            });
          }
        });
      }
    });

    if (!addressVal) {
      return result;
    }

    return result.map((item) => {
      const price = get(priceInCurrentCurrency(item.asset));
      return {
        ...item,
        fiatValue: price.multipliedBy(item.amount),
        price,
      };
    }).sort((a, b) => sortDesc(a.fiatValue, b.fiatValue));
  });

  const getAssetDetail = (
    asset: MaybeRef<string>,
    chain: MaybeRef<string>,
  ): ComputedRef<TradableAsset | undefined> => computed<TradableAsset | undefined>(() => get(allOwnedAssets)
    .find(item => item.asset === get(asset) && item.chain === get(chain)));

  return {
    allOwnedAssets,
    getAssetDetail,
  };
}
