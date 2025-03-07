import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithoutSessionStatus } from '@/services/utils';

interface UseAssetSpamApiReturn {
  markAssetsAsSpam: (tokens: string[]) => Promise<boolean>;
  removeAssetFromSpamList: (token: string) => Promise<boolean>;
}

export function useAssetSpamApi(): UseAssetSpamApiReturn {
  const markAssetsAsSpam = async (tokens: string[]): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/assets/evm/spam/',
      {
        tokens,
      },
      {
        validateStatus: validWithoutSessionStatus,
      },
    );

    return handleResponse(response);
  };

  const removeAssetFromSpamList = async (token: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/evm/spam/', {
      data: { token },
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  return {
    markAssetsAsSpam,
    removeAssetFromSpamList,
  };
}
