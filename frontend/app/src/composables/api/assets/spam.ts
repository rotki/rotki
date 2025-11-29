import { api } from '@/modules/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';

interface UseAssetSpamApiReturn {
  markAssetsAsSpam: (tokens: string[]) => Promise<boolean>;
  removeAssetFromSpamList: (token: string) => Promise<boolean>;
}

export function useAssetSpamApi(): UseAssetSpamApiReturn {
  const markAssetsAsSpam = async (tokens: string[]): Promise<boolean> => api.post<boolean>(
    '/assets/evm/spam/',
    {
      tokens,
    },
    {
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    },
  );

  const removeAssetFromSpamList = async (token: string): Promise<boolean> => api.delete<boolean>('/assets/evm/spam/', {
    body: { token },
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  return {
    markAssetsAsSpam,
    removeAssetFromSpamList,
  };
}
