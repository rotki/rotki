import { type MaybeRef } from '@vueuse/core';
import { getIdentifierFromSymbolMap } from '@rotki/common/lib/data';
import { Routes } from '@/router/routes';
import { useAssetIconApi } from '@/services/assets/icon-api';
import { type TradeLocationData, useTradeLocations } from '@/types/trades';
import { assert } from '@/utils/assertions';
import { isBlockchain } from '@/types/blockchain/chains';
import { useSupportedChains } from '@/composables/info/chains';

export const useLocationInfo = () => {
  const { tradeLocations } = useTradeLocations();
  const { assetImageUrl } = useAssetIconApi();
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
        icon: assetImageUrl(assetId),
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
