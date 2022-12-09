import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { Routes } from '@/router/routes';
import { useAssetIconApi } from '@/services/assets/icon-api';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { type TradeLocationData, useTradeLocations } from '@/types/trades';
import { assert } from '@/utils/assertions';

export const useLocationInfo = () => {
  const isSupportedBlockchain = (identifier: string): boolean => {
    return Object.values(Blockchain).includes(identifier as any);
  };

  const { assetName } = useAssetInfoRetrieval();
  const { tradeLocations } = useTradeLocations();
  const { assetImageUrl } = useAssetIconApi();

  const getLocation = (identifier: MaybeRef<string>): TradeLocationData => {
    const id = get(identifier);
    if (isSupportedBlockchain(id)) {
      return {
        name: get(assetName(id)),
        identifier: id,
        exchange: false,
        imageIcon: true,
        icon: assetImageUrl(id),
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
