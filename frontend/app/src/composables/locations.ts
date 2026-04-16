import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import type { TradeLocationData } from '@/modules/history/trade/location';
import { useSupportedChains } from '@/composables/info/chains';
import { useLocationStore } from '@/modules/common/use-location-store';
import { isBlockchain } from '@/modules/onchain/chains';

interface UseLocationsReturn {
  getExchangeName: (location: string) => string;
  getLocationData: (id: string) => TradeLocationData | undefined;
  tradeLocations: DeepReadonly<Ref<TradeLocationData[]>>;
  useLocationData: (identifier: MaybeRefOrGetter<string | null>) => ComputedRef<TradeLocationData | undefined>;
}

export function useLocations(): UseLocationsReturn {
  const { tradeLocations } = storeToRefs(useLocationStore());
  const { getBlockchainRedirectLink, getChainImageUrl, getChainName, matchChain } = useSupportedChains();

  function getLocationData(id: string): TradeLocationData | undefined {
    const blockchainId = id.split(' ').join('_');

    const chain = matchChain(blockchainId);
    if (chain && isBlockchain(blockchainId) && isBlockchain(chain)) {
      const detailPath = getBlockchainRedirectLink(blockchainId);
      return {
        detailPath,
        identifier: blockchainId,
        image: getChainImageUrl(blockchainId),
        name: getChainName(blockchainId),
      };
    }

    const locations = get(tradeLocations);
    return locations.find(location => location.identifier === id);
  }

  function useLocationData(identifier: MaybeRefOrGetter<string | null>): ComputedRef<TradeLocationData | undefined> {
    return computed<TradeLocationData | undefined>(() => {
      const id = toValue(identifier);
      if (!id)
        return undefined;

      return getLocationData(id);
    });
  }

  function getExchangeName(location: string): string {
    const exchange = get(tradeLocations).find(tl => tl.identifier === location);
    return exchange?.name ?? '';
  }

  return {
    getExchangeName,
    getLocationData,
    tradeLocations: readonly(tradeLocations),
    useLocationData,
  };
}
