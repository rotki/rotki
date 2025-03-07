import type { ActionResult } from '@rotki/common';
import { setupTransformer, snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';
import { type ExternalServiceKey, ExternalServiceKeys } from '@/types/user';

interface UseExternalServicesApiReturn {
  queryExternalServices: () => Promise<ExternalServiceKeys>;
  setExternalServices: (keys: ExternalServiceKey[]) => Promise<ExternalServiceKeys>;
  deleteExternalServices: (serviceToDelete: string) => Promise<ExternalServiceKeys>;
}

export function useExternalServicesApi(): UseExternalServicesApiReturn {
  const queryExternalServices = async (): Promise<ExternalServiceKeys> => {
    const response = await api.instance.get<ActionResult<ExternalServiceKeys>>('/external_services', {
      transformResponse: setupTransformer(true),
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
        transformResponse: setupTransformer(true),
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
      transformResponse: setupTransformer(true),
      validateStatus: validStatus,
    });

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  return {
    deleteExternalServices,
    queryExternalServices,
    setExternalServices,
  };
}
