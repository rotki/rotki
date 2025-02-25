import { snakeCaseTransformer } from '@/services/axios-transformers';
import { handleResponse } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { BackendInfo } from '@/types/backend';
import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';

interface UseInfoApiReturn {
  info: (checkForUpdates?: boolean) => Promise<BackendInfo>;
  ping: () => Promise<PendingTask>;
}

export function useInfoApi(): UseInfoApiReturn {
  const info = async (checkForUpdates = false): Promise<BackendInfo> => {
    const response = await api.instance.get<ActionResult<BackendInfo>>('/info', {
      params: snakeCaseTransformer({
        checkForUpdates,
      }),
    });
    return BackendInfo.parse(handleResponse(response));
  };

  const ping = async (): Promise<PendingTask> => {
    const ping = await api.instance.get<ActionResult<PendingTask>>('/ping'); // no validate status here since defaults work
    return handleResponse(ping);
  };

  return {
    info,
    ping,
  };
}
