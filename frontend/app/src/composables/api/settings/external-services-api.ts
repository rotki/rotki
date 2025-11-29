import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { type ExternalServiceKey, ExternalServiceKeys } from '@/types/user';

interface UseExternalServicesApiReturn {
  queryExternalServices: () => Promise<ExternalServiceKeys>;
  setExternalServices: (keys: ExternalServiceKey[]) => Promise<ExternalServiceKeys>;
  deleteExternalServices: (serviceToDelete: string) => Promise<ExternalServiceKeys>;
}

export function useExternalServicesApi(): UseExternalServicesApiReturn {
  const queryExternalServices = async (): Promise<ExternalServiceKeys> => {
    const response = await api.get<ExternalServiceKeys>('/external_services', {
      skipRootCamelCase: true,
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return ExternalServiceKeys.parse(response);
  };

  const setExternalServices = async (keys: ExternalServiceKey[]): Promise<ExternalServiceKeys> => {
    const response = await api.put<ExternalServiceKeys>(
      '/external_services',
      { services: keys },
      {
        skipRootCamelCase: true,
      },
    );

    return ExternalServiceKeys.parse(response);
  };

  const deleteExternalServices = async (serviceToDelete: string): Promise<ExternalServiceKeys> => {
    const response = await api.delete<ExternalServiceKeys>('/external_services', {
      body: { services: [serviceToDelete] },
      skipRootCamelCase: true,
    });

    return ExternalServiceKeys.parse(response);
  };

  return {
    deleteExternalServices,
    queryExternalServices,
    setExternalServices,
  };
}
