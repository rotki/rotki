import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';

export interface MoneriumProfile {
  id: string;
  name?: string;
  kind?: string;
}

export interface MoneriumStatus {
  authenticated: boolean;
  userEmail?: string;
  defaultProfileId?: string;
  profiles?: MoneriumProfile[];
  expiresAt?: number;
  tokenType?: string;
}

export interface MoneriumAuthResult {
  success: boolean;
  message: string;
  userEmail?: string;
  defaultProfileId?: string;
  profiles?: MoneriumProfile[];
}

interface UseMoneriumOAuthApiReturn {
  getStatus: () => Promise<MoneriumStatus>;
  completeOAuth: (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ) => Promise<MoneriumAuthResult>;
  disconnect: () => Promise<{ success: boolean }>;
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
