import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { type PremiumDevicePayload, PremiumDevicesResponse } from './premium';

interface UsePremiumDevicesApiReturn {
  fetchPremiumDevices: () => Promise<PremiumDevicesResponse>;
  updatePremiumDevice: (payload: PremiumDevicePayload) => Promise<boolean>;
  deletePremiumDevice: (deviceIdentifier: string) => Promise<boolean>;
}

export function usePremiumDevicesApi(): UsePremiumDevicesApiReturn {
  const fetchPremiumDevices = async (): Promise<PremiumDevicesResponse> => {
    const response = await api.instance.get<ActionResult<PremiumDevicesResponse>>(
      '/premium/devices',
      { validateStatus: validStatus },
    );

    return PremiumDevicesResponse.parse(handleResponse(response));
  };

  const updatePremiumDevice = async (payload: PremiumDevicePayload): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/premium/devices',
      snakeCaseTransformer(payload),
      { validateStatus: validStatus },
    );

    return handleResponse(response);
  };

  const deletePremiumDevice = async (deviceIdentifier: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/premium/devices',
      {
        data: snakeCaseTransformer({ deviceIdentifier }),
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    deletePremiumDevice,
    fetchPremiumDevices,
    updatePremiumDevice,
  };
}
