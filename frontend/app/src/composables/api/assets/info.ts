import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithoutSessionStatus } from '@/services/utils';
import { AssetMap, AssetsWithId } from '@/types/asset';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import type { EvmChainAddress } from '@/types/history/events';

export interface AssetSearchParams {
  value: string;
  evmChain?: string;
  address?: string;
  limit?: number;
  searchNfts?: boolean;
  signal?: AbortSignal;
}

interface UseAssetInfoApiReturn {
  assetMapping: (identifiers: string[]) => Promise<AssetMap>;
  assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>;
  erc20details: (payload: EvmChainAddress) => Promise<PendingTask>;
}

export function useAssetInfoApi(): UseAssetInfoApiReturn {
  const assetMapping = async (identifiers: string[]): Promise<AssetMap> => {
    const response = await api.instance.post<ActionResult<AssetMap>>(
      '/assets/mappings',
      { identifiers },
      {
        validateStatus: validStatus,
      },
    );
    return AssetMap.parse(handleResponse(response));
  };

  const assetSearch = async (params: AssetSearchParams): Promise<AssetsWithId> => {
    const {
      address,
      evmChain,
      limit,
      searchNfts,
      signal,
      value,
    } = params;
    const response = await api.instance.post<ActionResult<AssetsWithId>>(
      '/assets/search/levenshtein',
      snakeCaseTransformer({
        address,
        evmChain,
        limit: limit || 25,
        searchNfts,
        value,
      }),
      {
        signal,
        validateStatus: validStatus,
      },
    );
    return AssetsWithId.parse(handleResponse(response));
  };

  const erc20details = async (payload: EvmChainAddress): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('/blockchains/evm/erc20details', {
      params: snakeCaseTransformer({
        asyncQuery: true,
        ...payload,
      }),
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  return {
    assetMapping,
    assetSearch,
    erc20details,
  };
}
