import { api } from '@/modules/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';

interface UseAssetWhitelistApiReturn {
  getWhitelistedAssets: () => Promise<string[]>;
  addAssetToWhitelist: (token: string) => Promise<boolean>;
  removeAssetFromWhitelist: (token: string) => Promise<boolean>;
}

export function useAssetWhitelistApi(): UseAssetWhitelistApiReturn {
  const getWhitelistedAssets = async (): Promise<string[]> => api.get<string[]>('/assets/ignored/whitelist', {
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const addAssetToWhitelist = async (token: string): Promise<boolean> => api.post<boolean>(
    '/assets/ignored/whitelist',
    {
      token,
    },
    {
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    },
  );

  const removeAssetFromWhitelist = async (token: string): Promise<boolean> => api.delete<boolean>('/assets/ignored/whitelist', {
    body: { token },
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  return {
    addAssetToWhitelist,
    getWhitelistedAssets,
    removeAssetFromWhitelist,
  };
}
