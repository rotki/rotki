import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithoutSessionStatus } from '@/services/utils';

export const useAssetWhitelistApi = () => {
  const getWhitelistedAssets = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/assets/ignored/whitelist',
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const addAssetToWhitelist = async (token: string): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/assets/ignored/whitelist',
      {
        token
      },
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const removeAssetFromWhitelist = async (token: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/ignored/whitelist',
      {
        data: { token },
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getWhitelistedAssets,
    addAssetToWhitelist,
    removeAssetFromWhitelist
  };
};
