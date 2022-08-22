import { Blockchain } from '@rotki/common/lib/blockchain';
import { get } from '@vueuse/core';
import { tradeLocations } from '@/components/history/consts';
import { Routes } from '@/router/routes';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { assert } from '@/utils/assertions';

export const setupLocationInfo = () => {
  const isSupportedBlockchain = (identifier: string): boolean => {
    return Object.values(Blockchain).includes(identifier as any);
  };

  const getLocation = (identifier: string) => {
    const { assetName } = useAssetInfoRetrieval();

    if (isSupportedBlockchain(identifier)) {
      return {
        name: get(assetName(identifier)),
        identifier: identifier,
        exchange: false,
        imageIcon: true,
        icon: `${api.serverUrl}/api/1/assets/${encodeURIComponent(
          identifier
        )}/icon`,
        detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route}#blockchain-balances-${identifier}`
      };
    }

    const locationFound = tradeLocations.find(
      location => location.identifier === identifier
    );
    assert(!!locationFound, 'location should not be falsy');
    return locationFound;
  };

  return {
    getLocation
  };
};
