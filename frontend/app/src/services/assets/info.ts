import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus
} from '@/services/utils';
import { AssetMap, AssetsWithId } from '@/types/assets';

export const useAssetInfoApi = () => {
  const assetMapping = async (identifiers: string[]): Promise<AssetMap> => {
    const response = await api.instance.post<ActionResult<AssetMap>>(
      '/assets/mappings',
      { identifiers },
      {
        validateStatus: validStatus
      }
    );
    return AssetMap.parse(handleResponse(response));
  };

  const assetSearch = async (
    keyword: string,
    limit = 25,
    searchNfts = false,
    signal?: AbortSignal
  ): Promise<AssetsWithId> => {
    const response = await api.instance.post<ActionResult<AssetsWithId>>(
      '/assets/search/levenshtein',
      axiosSnakeCaseTransformer({
        value: keyword,
        limit,
        searchNfts
      }),
      {
        validateStatus: validStatus,
        signal
      }
    );
    return AssetsWithId.parse(handleResponse(response));
  };

  const erc20details = async (address: string): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/ETH/erc20details',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          address
        }),
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  return {
    assetMapping,
    assetSearch,
    erc20details
  };
};
