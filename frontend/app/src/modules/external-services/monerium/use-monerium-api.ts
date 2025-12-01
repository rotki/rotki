import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import {
  type MoneriumAuthResult,
  MoneriumAuthResultSchema,
  type MoneriumDisconnectResult,
  MoneriumDisconnectResultSchema,
  type MoneriumStatus,
  MoneriumStatusSchema,
} from './types';

interface UseMoneriumOAuthApiReturn {
  completeOAuth: (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ) => Promise<MoneriumAuthResult>;
  disconnect: () => Promise<MoneriumDisconnectResult>;
  getStatus: () => Promise<MoneriumStatus>;
}

const basePath = '/services/monerium';

export function useMoneriumOAuthApi(): UseMoneriumOAuthApiReturn {
  const getStatus = async (): Promise<MoneriumStatus> => {
    const response = await api.get<MoneriumStatus>(basePath, {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    return MoneriumStatusSchema.parse(response);
  };

  const completeOAuth = async (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ): Promise<MoneriumAuthResult> => {
    const response = await api.put<MoneriumAuthResult>(
      basePath,
      {
        accessToken,
        expiresIn,
        refreshToken,
      },
      { validStatuses: VALID_WITH_SESSION_STATUS },
    );
    return MoneriumAuthResultSchema.parse(response);
  };

  const disconnect = async (): Promise<MoneriumDisconnectResult> => {
    const response = await api.delete<MoneriumDisconnectResult>(basePath, {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    return MoneriumDisconnectResultSchema.parse(response);
  };

  return {
    completeOAuth,
    disconnect,
    getStatus,
  };
}
