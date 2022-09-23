import { ActionResult } from '@rotki/common/lib/data';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
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
        validateStatus: validStatus,
        transformResponse: setupTransformer([], true)
      }
    );
    return AssetMap.parse(handleResponse(response));
  };

  const assetSearch = async (
    keyword: string,
    limit: number = 25,
    signal?: AbortSignal
  ): Promise<AssetsWithId> => {
    const response = await api.instance.post<ActionResult<AssetsWithId>>(
      '/assets/search/levenshtein',
      {
        value: keyword,
        limit
      },
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
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
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
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
