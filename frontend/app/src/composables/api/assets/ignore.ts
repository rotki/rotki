import { defaultApiUrls } from '@/modules/api/api-urls';
import { api } from '@/modules/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';
import { IgnoredAssetResponse } from '@/types/asset';

interface UseAssetIgnoreApiReturn {
  getIgnoredAssets: () => Promise<string[]>;
  addIgnoredAssets: (assets: string[]) => Promise<IgnoredAssetResponse>;
  removeIgnoredAssets: (assets: string[]) => Promise<IgnoredAssetResponse>;
}

export function useAssetIgnoreApi(): UseAssetIgnoreApiReturn {
  const getIgnoredAssets = async (): Promise<string[]> => api.get<string[]>('/assets/ignored', {
    baseURL: defaultApiUrls.colibriApiUrl,
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const addIgnoredAssets = async (assets: string[]): Promise<IgnoredAssetResponse> => {
    const response = await api.put<IgnoredAssetResponse>(
      '/assets/ignored',
      {
        assets,
      },
    );

    return IgnoredAssetResponse.parse(response);
  };

  const removeIgnoredAssets = async (assets: string[]): Promise<IgnoredAssetResponse> => {
    const response = await api.delete<IgnoredAssetResponse>('/assets/ignored', {
      body: {
        assets,
      },
    });

    return IgnoredAssetResponse.parse(response);
  };

  return {
    addIgnoredAssets,
    getIgnoredAssets,
    removeIgnoredAssets,
  };
}
