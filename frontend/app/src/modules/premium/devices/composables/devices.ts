import { api } from '@/modules/api/rotki-api';
import { type PremiumDevicePayload, PremiumDevicesResponse } from './premium';

interface UsePremiumDevicesApiReturn {
  fetchPremiumDevices: () => Promise<PremiumDevicesResponse>;
  updatePremiumDevice: (payload: PremiumDevicePayload) => Promise<boolean>;
  deletePremiumDevice: (deviceIdentifier: string) => Promise<boolean>;
}

export function usePremiumDevicesApi(): UsePremiumDevicesApiReturn {
  const fetchPremiumDevices = async (): Promise<PremiumDevicesResponse> => {
    const response = await api.get<PremiumDevicesResponse>('/premium/devices');
    return PremiumDevicesResponse.parse(response);
  };

  const updatePremiumDevice = async (payload: PremiumDevicePayload): Promise<boolean> => api.patch<boolean>('/premium/devices', payload);

  const deletePremiumDevice = async (deviceIdentifier: string): Promise<boolean> => api.delete<boolean>('/premium/devices', {
    body: { deviceIdentifier },
  });

  return {
    deletePremiumDevice,
    fetchPremiumDevices,
    updatePremiumDevice,
  };
}
