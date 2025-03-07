import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithoutSessionStatus } from '@/services/utils';

interface UseAssetWhitelistApiReturn {
  getWhitelistedAssets: () => Promise<string[]>;
  addAssetToWhitelist: (token: string) => Promise<boolean>;
  removeAssetFromWhitelist: (token: string) => Promise<boolean>;
}

export function useAssetWhitelistApi(): UseAssetWhitelistApiReturn {
  const getWhitelistedAssets = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>('/assets/ignored/whitelist', {
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const addAssetToWhitelist = async (token: string): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/assets/ignored/whitelist',
      {
        token,
      },
      {
        validateStatus: validWithoutSessionStatus,
      },
    );

    return handleResponse(response);
  };

  const removeAssetFromWhitelist = async (token: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/ignored/whitelist', {
      data: { token },
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  return {
    addAssetToWhitelist,
    getWhitelistedAssets,
    removeAssetFromWhitelist,
  };
}
