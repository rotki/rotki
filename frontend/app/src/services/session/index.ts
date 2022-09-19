import { ActionResult } from '@rotki/common/lib/data';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';
import { Messages, PeriodicClientQueryResult } from '@/types/session';

export const useSessionApi = () => {
  async function consumeMessages(): Promise<Messages> {
    const response = await api.instance.get<ActionResult<Messages>>(
      '/messages'
    );

    return handleResponse(response);
  }

  async function fetchPeriodicData(): Promise<PeriodicClientQueryResult> {
    const response = await api.instance.get<
      ActionResult<PeriodicClientQueryResult>
    >('/periodic', {
      validateStatus: validWithSessionStatus,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  }

  return {
    consumeMessages,
    fetchPeriodicData
  };
};
