import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';
import { type ExternalServiceKey, ExternalServiceKeys } from '@/types/user';
import type { ActionResult } from '@rotki/common';

interface UseExternalServicesApiReturn {
  queryExternalServices: () => Promise<ExternalServiceKeys>;
  setExternalServices: (keys: ExternalServiceKey[]) => Promise<ExternalServiceKeys>;
  deleteExternalServices: (serviceToDelete: string) => Promise<ExternalServiceKeys>;
}

export function useExternalServicesApi(): UseExternalServicesApiReturn {
  const queryExternalServices = async (): Promise<ExternalServiceKeys> => {
    const response = await api.instance.get<ActionResult<ExternalServiceKeys>>('/external_services', {
      validateStatus: validWithSessionStatus,
    });

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  const setExternalServices = async (keys: ExternalServiceKey[]): Promise<ExternalServiceKeys> => {
    const response = await api.instance.put<ActionResult<ExternalServiceKeys>>(
      '/external_services',
      snakeCaseTransformer({
        services: keys,
      }),
      {
        validateStatus: validStatus,
      },
    );

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  const deleteExternalServices = async (serviceToDelete: string): Promise<ExternalServiceKeys> => {
    const response = await api.instance.delete<ActionResult<ExternalServiceKeys>>('/external_services', {
      data: {
        services: [serviceToDelete],
      },
      validateStatus: validStatus,
    });

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  return {
    queryExternalServices,
    setExternalServices,
    deleteExternalServices,
  };
}
