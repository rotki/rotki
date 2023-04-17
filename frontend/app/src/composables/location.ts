import { type MaybeRef } from '@vueuse/core';
import { getIdentifierFromSymbolMap } from '@rotki/common/lib/data';
import { Routes } from '@/router/routes';
import { isBlockchain } from '@/types/blockchain/chains';
import { type TradeLocationData } from '@/types/history/trade/location';

export const useLocationInfo = () => {
  const { tradeLocations } = useTradeLocations();
  const { getAssetImageUrl } = useAssetIcon();
  const { getChainInfoById } = useSupportedChains();

  const getLocation = (identifier: MaybeRef<string>): TradeLocationData => {
    const id = get(identifier);
    if (isBlockchain(id)) {
      const assetId = getIdentifierFromSymbolMap(id);

      return {
        name: get(getChainInfoById(id))?.name || id,
        identifier: assetId,
        exchange: false,
        imageIcon: true,
        icon: getAssetImageUrl(assetId),
        detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN}#blockchain-balances-${id}`
      };
    }

    const locationFound = get(tradeLocations).find(
      location => location.identifier === id
    );
    assert(!!locationFound, 'location should not be falsy');
    return locationFound;
  };

  return {
    getLocation
  };
};
