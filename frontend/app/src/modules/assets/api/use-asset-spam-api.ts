import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/core/api/utils';

interface UseAssetSpamApiReturn {
  markAssetsAsSpam: (tokens: string[]) => Promise<boolean>;
  removeAssetFromSpamList: (token: string) => Promise<boolean>;
}

export function useAssetSpamApi(): UseAssetSpamApiReturn {
  const markAssetsAsSpam = async (tokens: string[]): Promise<boolean> => api.post<boolean>(
    '/assets/spam',
    {
      tokens,
    },
    {
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    },
  );

  const removeAssetFromSpamList = async (token: string): Promise<boolean> => api.delete<boolean>('/assets/spam', {
    body: { token },
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  return {
    markAssetsAsSpam,
    removeAssetFromSpamList,
  };
}
