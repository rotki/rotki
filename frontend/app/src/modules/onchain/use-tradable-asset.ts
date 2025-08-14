import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { TradableAsset, TradableAssetWithoutValue } from '@/modules/onchain/types';
import type { BlockchainAssetBalances, EthBalance, ProtocolBalances } from '@/types/blockchain/balances';
import { Zero } from '@rotki/common';
import { useSupportedChains } from '@/composables/info/chains';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { sortDesc } from '@/utils/bignumbers';
import { useWalletStore } from './use-wallet-store';

interface UseTradableAssetReturn {
  allOwnedAssets: ComputedRef<TradableAsset[]>;
  getAssetDetail: (asset: MaybeRef<string>, chain: MaybeRef<string>) => ComputedRef<TradableAsset | undefined>;
}

export function useTradableAsset(address: MaybeRef<string | undefined>): UseTradableAssetReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { assetPriceInCurrentCurrency } = usePriceUtils();
  const { supportedChainsForConnectedAccount } = storeToRefs(useWalletStore());
  const { getNativeAsset, isEvm } = useSupportedChains();

  // Cache for memoized asset detail computed with size limit
  const assetDetailCache = new Map<string, ComputedRef<TradableAsset | undefined>>();
  const MAX_CACHE_SIZE = 50;

  // Helper function to process specific address balances
  const processAddressBalances = (
    chain: string,
    chainBalances: BlockchainAssetBalances,
    addressVal: string,
  ): TradableAssetWithoutValue[] => {
    const result: TradableAssetWithoutValue[] = [];
    const addressBalance: EthBalance | undefined = chainBalances[addressVal];

    if (!addressBalance?.assets) {
      return result;
    }

    for (const [asset, balance] of Object.entries(addressBalance.assets)) {
      const protocolBalance: ProtocolBalances = balance;
      if (!protocolBalance.address?.amount) {
        continue;
      }
      result.push({
        amount: protocolBalance.address.amount,
        asset,
        chain,
      });
    }

    return result;
  };

  // Helper function to process all addresses with deduplication
  const processAllAddressBalances = (
    chain: string,
    chainBalances: BlockchainAssetBalances,
  ): TradableAssetWithoutValue[] => {
    const result: TradableAssetWithoutValue[] = [];
    const seenAssets = new Map<string, boolean>();

    for (const addressBalance of Object.values(chainBalances)) {
      if (!addressBalance?.assets) {
        continue;
      }
      for (const [asset, balance] of Object.entries(addressBalance.assets)) {
        const protocolBalance: ProtocolBalances = balance;
        if (!(protocolBalance.address?.amount && !seenAssets.has(asset))) {
          continue;
        }
        seenAssets.set(asset, true);
        result.push({
          amount: Zero,
          asset,
          chain,
        });
      }
    }

    return result;
  };

  // Helper function to batch price calculations
  const enhanceWithPrices = (assets: TradableAssetWithoutValue[]): TradableAsset[] => {
    // Batch price lookups to avoid individual calls
    const uniqueAssets = [...new Set(assets.map(a => a.asset))];
    const priceCache = new Map<string, any>();

    // Pre-fetch all prices
    for (const assetId of uniqueAssets) {
      priceCache.set(assetId, get(assetPriceInCurrentCurrency(assetId)));
    }

    return assets.map((item) => {
      const price = priceCache.get(item.asset)!;
      return {
        ...item,
        fiatValue: price.multipliedBy(item.amount),
        price,
      };
    }).sort((a, b) => {
      // Check if either asset is a native token
      const aNative = getNativeAsset(a.chain) === a.asset;
      const bNative = getNativeAsset(b.chain) === b.asset;

      // If one is native and the other isn't, prioritize the native token
      if (aNative && !bNative)
        return -1;
      if (!aNative && bNative)
        return 1;

      // If both are native or both are not native, sort by fiat value
      return sortDesc(a.fiatValue, b.fiatValue);
    });
  };

  const allOwnedAssets = computed<TradableAsset[]>(() => {
    const addressVal = get(address);
    const supportedChains = get(supportedChainsForConnectedAccount);
    const balancesData = get(balances);

    const result: TradableAssetWithoutValue[] = [];

    // Single pass through balances with early filtering
    for (const [chain, chainBalances] of Object.entries(balancesData)) {
      // Early exit conditions
      if (!get(isEvm(chain)) || !supportedChains.includes(chain)) {
        continue;
      }

      if (addressVal) {
        result.push(...processAddressBalances(chain, chainBalances, addressVal));
      }
      else {
        result.push(...processAllAddressBalances(chain, chainBalances));
      }
    }

    // Return early if no address provided (no price calculation needed)
    if (!addressVal) {
      return result;
    }

    // Enhance with prices and sort
    return enhanceWithPrices(result);
  });

  const createAssetDetailComputed = (
    asset: MaybeRef<string>,
    chain: MaybeRef<string>,
  ): ComputedRef<TradableAsset | undefined> => computed(() =>
    get(allOwnedAssets).find(item =>
      item.asset === get(asset) && item.chain === get(chain),
    ),
  );

  const getAssetDetail = (
    asset: MaybeRef<string>,
    chain: MaybeRef<string>,
  ): ComputedRef<TradableAsset | undefined> => {
    const cacheKey = computed<string>(() => `${get(asset)}-${get(chain)}`);

    return computed<TradableAsset | undefined>(() => {
      const key = get(cacheKey);

      if (!assetDetailCache.has(key)) {
        // If cache is at max size, remove oldest entry (first inserted)
        if (assetDetailCache.size >= MAX_CACHE_SIZE) {
          const firstKey = assetDetailCache.keys().next().value;
          if (firstKey) {
            assetDetailCache.delete(firstKey);
          }
        }

        const detailComputed = createAssetDetailComputed(asset, chain);
        assetDetailCache.set(key, detailComputed);
      }

      const cachedDetail = assetDetailCache.get(key);
      return cachedDetail ? get(cachedDetail) : undefined;
    });
  };

  return {
    allOwnedAssets,
    getAssetDetail,
  };
}
