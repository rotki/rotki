import type { ActionResult } from '@rotki/common';
import type { Messages, PeriodicClientQueryResult } from '@/types/session';
import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';

interface UseSessionApiReturn {
  consumeMessages: () => Promise<Messages>;
  fetchPeriodicData: () => Promise<PeriodicClientQueryResult>;
  refreshGeneralCacheTask: (cacheProtocol: string) => Promise<PendingTask>;
  getRefreshableGeneralCaches: () => Promise<string[]>;
}

export function useSessionApi(): UseSessionApiReturn {
  const consumeMessages = async (): Promise<Messages> => {
    const response = await api.instance.get<ActionResult<Messages>>('/messages');

    return handleResponse(response);
  };

  const fetchPeriodicData = async (): Promise<PeriodicClientQueryResult> => {
    const response = await api.instance.get<ActionResult<PeriodicClientQueryResult>>('/periodic', {
      validateStatus: validWithSessionStatus,
    });

    return handleResponse(response);
  };

  const refreshGeneralCacheTask = async (cacheProtocol: string): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/protocols/data/refresh',
      snakeCaseTransformer({ asyncQuery: true, cacheProtocol }),
      {
        validateStatus: validWithSessionStatus,
      },
    );

    return handleResponse(response);
  };

  const getRefreshableGeneralCaches = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/protocols/data/refresh',
      snakeCaseTransformer({ asyncQuery: true }),
    );

    return handleResponse(response);
  };

  return {
    consumeMessages,
    fetchPeriodicData,
    getRefreshableGeneralCaches,
    refreshGeneralCacheTask,
  };
}
