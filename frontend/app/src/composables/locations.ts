import { type MaybeRef } from '@vueuse/core';
import { Routes } from '@/router/routes';
import { isBlockchain } from '@/types/blockchain/chains';
import { type TradeLocationData } from '@/types/history/trade/location';

export const useLocations = createSharedComposable(() => {
  const { tradeLocations } = storeToRefs(useLocationStore());

  const exchangeName = (location: MaybeRef<string>): string => {
    const exchange = get(tradeLocations).find(
      tl => tl.identifier === get(location)
    );

    assert(!!exchange, 'location should not be falsy');
    return exchange.name;
  };

  const { getChainName, getChainImageUrl } = useSupportedChains();

  const locationData = (
    identifier: MaybeRef<string>
  ): ComputedRef<TradeLocationData | null> =>
    computed(() => {
      const id = get(identifier);
      const blockchainId = id.split(' ').join('_');

      if (isBlockchain(blockchainId)) {
        return {
          name: get(getChainName(blockchainId)),
          identifier: blockchainId,
          image: get(getChainImageUrl(blockchainId)),
          detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN}#blockchain-balances-${id}`
        };
      }

      const locations = get(tradeLocations);
      return locations.find(location => location.identifier === id) ?? null;
    });

  const getLocationData = (identifier: string): TradeLocationData | null =>
    get(locationData(identifier));

  return {
    tradeLocations,
    exchangeName,
    getLocationData,
    locationData
  };
});
