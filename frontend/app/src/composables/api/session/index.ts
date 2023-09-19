import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';
import { type Messages, type PeriodicClientQueryResult } from '@/types/session';
import { type PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-tranformers';

export const useSessionApi = () => {
  const consumeMessages = async (): Promise<Messages> => {
    const response =
      await api.instance.get<ActionResult<Messages>>('/messages');

    return handleResponse(response);
  };

  const fetchPeriodicData = async (): Promise<PeriodicClientQueryResult> => {
    const response = await api.instance.get<
      ActionResult<PeriodicClientQueryResult>
    >('/periodic', {
      validateStatus: validWithSessionStatus
    });

    return handleResponse(response);
  };

  const refreshGeneralCacheTask = async (): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/cache/general/refresh',
      snakeCaseTransformer({ asyncQuery: true }),
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response);
  };

  return {
    consumeMessages,
    fetchPeriodicData,
    refreshGeneralCacheTask
  };
};
