import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithoutSessionStatus } from '@/services/utils';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { IgnoredAssetResponse } from '@/types/asset';
import type { ActionResult } from '@rotki/common';

interface UseAssetIgnoreApiReturn {
  getIgnoredAssets: () => Promise<string[]>;
  addIgnoredAssets: (assets: string[]) => Promise<IgnoredAssetResponse>;
  removeIgnoredAssets: (assets: string[]) => Promise<IgnoredAssetResponse>;
}

export function useAssetIgnoreApi(): UseAssetIgnoreApiReturn {
  const getIgnoredAssets = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>('/assets/ignored', {
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const addIgnoredAssets = async (assets: string[]): Promise<IgnoredAssetResponse> => {
    const response = await api.instance.put<ActionResult<IgnoredAssetResponse>>(
      '/assets/ignored',
      snakeCaseTransformer({
        assets,
      }),
      {
        validateStatus: validStatus,
      },
    );

    return IgnoredAssetResponse.parse(handleResponse(response));
  };

  const removeIgnoredAssets = async (assets: string[]): Promise<IgnoredAssetResponse> => {
    const response = await api.instance.delete<ActionResult<IgnoredAssetResponse>>('/assets/ignored', {
      data: {
        assets,
      },
      validateStatus: validStatus,
    });

    return IgnoredAssetResponse.parse(handleResponse(response));
  };

  return {
    addIgnoredAssets,
    getIgnoredAssets,
    removeIgnoredAssets,
  };
}
