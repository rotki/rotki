import { getIdentifierFromSymbolMap } from '@rotki/common/lib/data';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { Routes } from '@/router/routes';
import { isBlockchain } from '@/types/blockchain/chains';
import {
  type TradeLocation,
  type TradeLocationData
} from '@/types/history/trade/location';

export const useLocations = createSharedComposable(() => {
  const { tradeLocations } = storeToRefs(useLocationStore());

  const exchangeName = (location: MaybeRef<TradeLocation>): string => {
    const exchange = get(tradeLocations).find(
      tl => tl.identifier === get(location)
    );

    assert(!!exchange, 'location should not be falsy');
    return exchange.name;
  };

  const { getAssetImageUrl } = useAssetIcon();
  const { getChainInfoById } = useSupportedChains();

  const locationData = (
    identifier: MaybeRef<string>
  ): ComputedRef<TradeLocationData | null> =>
    computed(() => {
      const id = get(identifier);

      if (isBlockchain(id)) {
        const assetId = getIdentifierFromSymbolMap(id);

        return {
          name: get(getChainInfoById(id))?.name || id,
          identifier: assetId,
          image: getAssetImageUrl(assetId),
          detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN}#blockchain-balances-${id}`
        };
      }

      const locations = get(tradeLocations);
      return locations.find(location => location.identifier === id) ?? null;
    });

  const getLocationData = (
    identifier: TradeLocation
  ): TradeLocationData | null => get(locationData(identifier));

  return {
    tradeLocations,
    exchangeName,
    getLocationData,
    locationData
  };
});
