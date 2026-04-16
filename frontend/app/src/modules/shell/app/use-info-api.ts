import { api } from '@/modules/core/api/rotki-api';
import { BackendInfo } from '@/modules/shell/app/backend';

interface UseInfoApiReturn {
  info: (checkForUpdates?: boolean) => Promise<BackendInfo>;
  ping: () => Promise<boolean>;
}

export function useInfoApi(): UseInfoApiReturn {
  const info = async (checkForUpdates = false): Promise<BackendInfo> => {
    const response = await api.get<BackendInfo>('/info', {
      query: { checkForUpdates },
    });
    return BackendInfo.parse(response);
  };

  const ping = async (): Promise<boolean> => api.get<boolean>('/ping');

  return {
    info,
    ping,
  };
}
