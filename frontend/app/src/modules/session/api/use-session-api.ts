import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import {
  type Messages,
  MessagesSchema,
  type PeriodicClientQueryResult,
  PeriodicClientQueryResultSchema,
} from '@/modules/session/types';

interface UseSessionApiReturn {
  consumeMessages: () => Promise<Messages>;
  fetchPeriodicData: () => Promise<PeriodicClientQueryResult>;
  refreshGeneralCacheTask: (cacheProtocol: string) => Promise<PendingTask>;
  getRefreshableGeneralCaches: () => Promise<string[]>;
}

export function useSessionApi(): UseSessionApiReturn {
  const consumeMessages = async (): Promise<Messages> => {
    const response = await api.get<Messages>('/messages');
    return MessagesSchema.parse(response);
  };

  const fetchPeriodicData = async (): Promise<PeriodicClientQueryResult> => {
    const response = await api.get<PeriodicClientQueryResult>('/periodic', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    return PeriodicClientQueryResultSchema.parse(response);
  };

  const refreshGeneralCacheTask = async (cacheProtocol: string): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/protocols/data/refresh',
      { asyncQuery: true, cacheProtocol },
      {
        validStatuses: VALID_WITH_SESSION_STATUS,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const getRefreshableGeneralCaches = async (): Promise<string[]> => api.get<string[]>('/protocols/data/refresh', {
    query: { asyncQuery: true },
  });

  return {
    consumeMessages,
    fetchPeriodicData,
    getRefreshableGeneralCaches,
    refreshGeneralCacheTask,
  };
}
