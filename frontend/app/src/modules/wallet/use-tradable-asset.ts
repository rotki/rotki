import type { ComputedRef, InjectionKey, MaybeRefOrGetter } from 'vue';
import type { BlockchainAssetBalances, EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { TradableAsset, TradableAssetWithoutValue } from '@/modules/wallet/types';
import { Zero } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useWalletStore } from './use-wallet-store';

interface UseInjectedTradableAssetReturn {
  allOwnedAssets: ComputedRef<TradableAsset[]>;
  getAssetDetail: (asset: MaybeRefOrGetter<string>, chain: MaybeRefOrGetter<string>) => ComputedRef<TradableAsset | undefined>;
}

export function useTradableAsset(address: MaybeRefOrGetter<string | undefined>): UseInjectedTradableAssetReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { supportedChainsForConnectedAccount } = storeToRefs(useWalletStore());
  const { getAssetPrice } = usePriceUtils();
  const { getNativeAsset, isEvm } = useSupportedChains();

  function collectAddressBalances(
    chain: string,
    chainBalances: BlockchainAssetBalances,
    addressVal: string,
    result: TradableAssetWithoutValue[],
  ): void {
    const addressBalance: EthBalance | undefined = chainBalances[addressVal];
    if (!addressBalance?.assets)
      return;

    for (const [asset, balance] of Object.entries(addressBalance.assets)) {
      if (balance.address?.amount) {
        result.push({ amount: balance.address.amount, asset, chain });
      }
    }
  }

  function collectDeduplicatedBalances(
    chain: string,
    chainBalances: BlockchainAssetBalances,
    result: TradableAssetWithoutValue[],
    seen: Set<string>,
  ): void {
    for (const addressBalance of Object.values(chainBalances)) {
      if (!addressBalance?.assets)
        continue;

      for (const [asset, balance] of Object.entries(addressBalance.assets)) {
        if (balance.address?.amount && !seen.has(asset)) {
          seen.add(asset);
          result.push({ amount: Zero, asset, chain });
        }
      }
    }
  }

  function enhanceWithPrices(assets: TradableAssetWithoutValue[]): TradableAsset[] {
    return assets.map((item) => {
      const price = getAssetPrice(item.asset);
      if (!price || price.lte(0)) {
        return { ...item, fiatValue: undefined, price: undefined };
      }
      return {
        ...item,
        fiatValue: price.multipliedBy(item.amount),
        price,
      };
    }).sort((a, b) => {
      const aNative = getNativeAsset(a.chain) === a.asset;
      const bNative = getNativeAsset(b.chain) === b.asset;

      if (aNative && !bNative)
        return -1;
      if (!aNative && bNative)
        return 1;

      return sortDesc(a.fiatValue ?? Zero, b.fiatValue ?? Zero);
    });
  }

  const allOwnedAssets = computed<TradableAsset[]>(() => {
    const addressVal = toValue(address);
    const supportedChains = get(supportedChainsForConnectedAccount);
    const balancesData = get(balances);

    const result: TradableAssetWithoutValue[] = [];
    const seen = new Set<string>();

    for (const [chain, chainBalances] of Object.entries(balancesData)) {
      if (!isEvm(chain) || !supportedChains.includes(chain))
        continue;

      if (addressVal)
        collectAddressBalances(chain, chainBalances, addressVal, result);
      else
        collectDeduplicatedBalances(chain, chainBalances, result, seen);
    }

    if (!addressVal)
      return result;

    return enhanceWithPrices(result);
  });

  function getAssetDetail(
    asset: MaybeRefOrGetter<string>,
    chain: MaybeRefOrGetter<string>,
  ): ComputedRef<TradableAsset | undefined> {
    return computed<TradableAsset | undefined>(() =>
      get(allOwnedAssets).find(item =>
        item.asset === toValue(asset) && item.chain === toValue(chain),
      ),
    );
  }

  return {

    allOwnedAssets,
    getAssetDetail,
  };
}

export const TradableAssetKey: InjectionKey<UseInjectedTradableAssetReturn> = Symbol('tradable-asset');

export function useInjectedTradableAsset(): UseInjectedTradableAssetReturn {
  const injected = inject(TradableAssetKey);
  if (!injected)
    throw new Error('useTradableAsset must be provided by a parent component');
  return injected;
}
