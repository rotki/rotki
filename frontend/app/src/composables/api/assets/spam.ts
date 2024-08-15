import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithoutSessionStatus } from '@/services/utils';
import type { ActionResult } from '@rotki/common';

export function useAssetSpamApi() {
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
