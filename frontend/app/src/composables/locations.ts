import type { MaybeRef } from '@vueuse/core';
import type { TradeLocationData } from '@/types/history/trade/location';
import { useSupportedChains } from '@/composables/info/chains';
import { useLocationStore } from '@/store/locations';
import { isBlockchain } from '@/types/blockchain/chains';

export const useLocations = createSharedComposable(() => {
  const { tradeLocations } = storeToRefs(useLocationStore());

  const exchangeName = (location: MaybeRef<string>): string => {
    const exchange = get(tradeLocations).find(tl => tl.identifier === get(location));

    return exchange?.name ?? '';
  };

  const { getBlockchainRedirectLink, getChainImageUrl, getChainName } = useSupportedChains();

  const locationData = (identifier: MaybeRef<string | null>): ComputedRef<TradeLocationData | null> => computed(() => {
    const id = get(identifier);
    if (!id)
      return null;

    const blockchainId = id.split(' ').join('_');

    if (isBlockchain(blockchainId)) {
      const detailPath = getBlockchainRedirectLink(blockchainId);
      return {
        detailPath,
        identifier: blockchainId,
        image: get(getChainImageUrl(blockchainId)),
        name: get(getChainName(blockchainId)),
      };
    }

    const locations = get(tradeLocations);
    return locations.find(location => location.identifier === id) ?? null;
  });

  const getLocationData = (identifier: string): TradeLocationData | null => get(locationData(identifier));

  return {
    exchangeName,
    getLocationData,
    locationData,
    tradeLocations,
  };
});
