import { type ActionResult } from '@rotki/common/lib/data';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus
} from '@/services/utils';
import { AssetMap, AssetsWithId } from '@/types/asset';
import { type PendingTask } from '@/types/task';
import { type EvmChainAddress } from '@/types/history/events';

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
      snakeCaseTransformer({
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

  const erc20details = async (
    payload: EvmChainAddress
  ): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/evm/erc20details',
      {
        params: snakeCaseTransformer({
          asyncQuery: true,
          ...payload
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
