import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import type { TradeLocationData } from '@/modules/core/common/location';
import { isBlockchain } from '@/modules/core/common/chains';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseLocationsReturn {
  getExchangeName: (location: string) => string;
  getLocationData: (id: string) => TradeLocationData | undefined;
  tradeLocations: DeepReadonly<Ref<TradeLocationData[]>>;
  useLocationData: (identifier: MaybeRefOrGetter<string | null>) => ComputedRef<TradeLocationData | undefined>;
}

const locationIndexes = new WeakMap<readonly TradeLocationData[], Map<string, TradeLocationData>>();

/**
 * The locations by identifier, built once per list.
 *
 * @remarks
 * A history page looks a location up for every row, so a linear search per lookup adds up. The
 * index is keyed by the list itself, so it is rebuilt only when the store produces a new list.
 */
function indexOf(locations: readonly TradeLocationData[]): Map<string, TradeLocationData> {
  let index = locationIndexes.get(locations);
  if (!index) {
    index = new Map(locations.map(location => [location.identifier, location]));
    locationIndexes.set(locations, index);
  }
  return index;
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

    return indexOf(get(tradeLocations)).get(id);
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
    return indexOf(get(tradeLocations)).get(location)?.name ?? '';
  }

  return {
    getExchangeName,
    getLocationData,
    tradeLocations: readonly(tradeLocations),
    useLocationData,
  };
}
