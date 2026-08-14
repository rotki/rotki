import type { NftHandling } from '@/modules/assets/nft-handling';
import type { EvmChainAddress } from '@/modules/history/events/event-payloads';
import { AssetMap, AssetsWithId } from '@/modules/assets/types';
import { RequestTarget } from '@/modules/core/api/constants';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

export interface AssetSearchParams {
  value: string;
  evmChain?: string;
  assetType?: string;
  address?: string;
  limit?: number;
  nftHandling?: NftHandling;
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
        target: RequestTarget.COLIBRI,
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
        limit: limit ?? 25,
        ...payload,
      },
      {
        target: RequestTarget.COLIBRI,
        retry: true,
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
