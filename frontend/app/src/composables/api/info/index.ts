import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { handleResponse } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';
import { BackendInfo } from '@/types/backend';

export const useInfoApi = () => {
  const info = async (checkForUpdates = false): Promise<BackendInfo> => {
    const response = await api.instance.get<ActionResult<BackendInfo>>(
      '/info',
      {
        params: axiosSnakeCaseTransformer({
          checkForUpdates
        })
      }
    );
    return BackendInfo.parse(handleResponse(response));
  };

  const ping = async (): Promise<PendingTask> => {
    const ping = await api.instance.get<ActionResult<PendingTask>>('/ping'); // no validate status here since defaults work
    return handleResponse(ping);
  };

  return {
    info,
    ping
  };
};
