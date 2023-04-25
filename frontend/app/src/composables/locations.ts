import { type ComputedRef, type Ref } from 'vue';
import { type MaybeRef } from '@vueuse/core';
import { getIdentifierFromSymbolMap } from '@rotki/common/lib/data';
import {
  type TradeLocation,
  type TradeLocationData
} from '@/types/history/trade/location';
import { type ActionDataEntry } from '@/types/action';
import { isBlockchain } from '@/types/blockchain/chains';
import { Routes } from '@/router/routes';

export const useLocations = createSharedComposable(() => {
  const { fetchAllLocations } = useHistoryApi();

  const { tc } = useI18n();

  const tradeLocations: Ref<TradeLocationData[]> = ref([]);

  const mapData = (
    locations: Record<string, Omit<ActionDataEntry, 'identifier'>>
  ) =>
    Object.entries(locations).map(([identifier, item]) => {
      const name = item.label
        ? item.label
        : tc(`backend_mappings.trade_location.${identifier}`)?.toString() ||
          toSentenceCase(identifier);

      const mapped = {
        identifier,
        ...item,
        name
      };

      if (item.image) {
        mapped.image = `./assets/images/protocols/${item.image}`;
      }

      return mapped;
    });

  const fetchAllTradeLocations = async () => {
    const data = await fetchAllLocations();

    set(tradeLocations, mapData(data.locations));
  };

  const exchangeName = (location: MaybeRef<TradeLocation>): string => {
    const exchange = get(tradeLocations).find(
      tl => tl.identifier === get(location)
    );

    assert(!!exchange, 'location should not be falsy');
    return exchange.name;
  };

  const { getAssetImageUrl } = useAssetIcon();
  const { getChainInfoById } = useSupportedChains();

  const getLocationData = (identifier: MaybeRef<string>): TradeLocationData => {
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

    const locationFound = get(tradeLocations).find(
      location => location.identifier === id
    );

    assert(!!locationFound, 'location should not be falsy');
    return locationFound;
  };

  const locationData = (
    identifier: MaybeRef<TradeLocation>
  ): ComputedRef<TradeLocationData> =>
    computed(() => getLocationData(get(identifier)));

  return {
    tradeLocations,
    exchangeName,
    getLocationData,
    fetchAllTradeLocations,
    locationData
  };
});
