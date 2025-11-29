import type { IgnorePayload } from '@/types/history/ignored';
import { api } from '@/modules/api/rotki-api';

interface UseHistoryIgnoringApiReturn {
  ignoreActions: (payload: IgnorePayload) => Promise<boolean>;
  unignoreActions: (payload: IgnorePayload) => Promise<boolean>;
}

export function useHistoryIgnoringApi(): UseHistoryIgnoringApiReturn {
  const ignoreActions = async (payload: IgnorePayload): Promise<boolean> => api.put<boolean>('/actions/ignored', payload);

  const unignoreActions = async (payload: IgnorePayload): Promise<boolean> => api.delete<boolean>('/actions/ignored', {
    body: payload,
  });

  return {
    ignoreActions,
    unignoreActions,
  };
}
