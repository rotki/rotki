import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import type { ActionResult } from '@rotki/common';
import type { IgnorePayload } from '@/types/history/ignored';

interface UseHistoryIgnoringApiReturn {
  ignoreActions: (payload: IgnorePayload) => Promise<boolean>;
  unignoreActions: (payload: IgnorePayload) => Promise<boolean>;
}

export function useHistoryIgnoringApi(): UseHistoryIgnoringApiReturn {
  const ignoreActions = async (payload: IgnorePayload): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>('/actions/ignored', snakeCaseTransformer(payload), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const unignoreActions = async (payload: IgnorePayload): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/actions/ignored', {
      data: snakeCaseTransformer(payload),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    ignoreActions,
    unignoreActions,
  };
}
