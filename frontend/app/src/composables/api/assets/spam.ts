import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithoutSessionStatus } from '@/services/utils';

export const useAssetSpamApi = () => {
  const markAssetAsSpam = async (token: string): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/assets/evm/spam/',
      {
        token
      },
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const removeAssetFromSpamList = async (token: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/evm/spam/',
      {
        data: { token },
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  return {
    markAssetAsSpam,
    removeAssetFromSpamList
  };
};
