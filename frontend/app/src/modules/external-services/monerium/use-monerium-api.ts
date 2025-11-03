import type { ActionResult } from '@rotki/common';
import type { MoneriumAuthResult, MoneriumStatus } from './types';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';

interface UseMoneriumOAuthApiReturn {
  completeOAuth: (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ) => Promise<MoneriumAuthResult>;
  disconnect: () => Promise<{ success: boolean }>;
  getStatus: () => Promise<MoneriumStatus>;
}

const basePath = '/services/monerium';

export function useMoneriumOAuthApi(): UseMoneriumOAuthApiReturn {
  const getStatus = async (): Promise<MoneriumStatus> => {
    const response = await api.instance.get<ActionResult<MoneriumStatus>>(
      basePath,
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const completeOAuth = async (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ): Promise<MoneriumAuthResult> => {
    const response = await api.instance.put<ActionResult<MoneriumAuthResult>>(
      basePath,
      snakeCaseTransformer({
        accessToken,
        expiresIn,
        refreshToken,
      }),
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const disconnect = async (): Promise<{ success: boolean }> => {
    const response = await api.instance.delete<ActionResult<{ success: boolean }>>(
      basePath,
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  return {
    completeOAuth,
    disconnect,
    getStatus,
  };
}
