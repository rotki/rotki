import type { EvmChainAddress } from '@/types/history/events';
import { defaultApiUrls } from '@/modules/api/api-urls';
import { api } from '@/modules/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';
import { AssetMap, AssetsWithId } from '@/types/asset';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

export interface AssetSearchParams {
  value: string;
  evmChain?: string;
  assetType?: string;
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
    const response = await api.post<AssetMap>(
      '/assets/mappings',
      { identifiers },
      {
        baseURL: defaultApiUrls.colibriApiUrl,
        retry: true,
      },
    );
    return AssetMap.parse(response);
  };

  const assetSearch = async (params: AssetSearchParams): Promise<AssetsWithId> => {
    const {
      limit,
      signal,
      ...payload
    } = params;
    const response = await api.post<AssetsWithId>(
      '/assets/search/levenshtein',
      {
        limit: limit || 25,
        ...payload,
      },
      {
        signal,
      },
    );
    return AssetsWithId.parse(response);
  };

  const erc20details = async (payload: EvmChainAddress): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/blockchains/evm/erc20details', {
      query: {
        asyncQuery: true,
        ...payload,
      },
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    assetMapping,
    assetSearch,
    erc20details,
  };
}
