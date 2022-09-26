import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import {
  ExternalServiceKey,
  ExternalServiceKeys,
  ExternalServiceName
} from '@/types/user';

export const useExternalServicesApi = () => {
  const queryExternalServices = async (): Promise<ExternalServiceKeys> => {
    const response = await api.instance.get<ActionResult<ExternalServiceKeys>>(
      '/external_services',
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  const setExternalServices = async (
    keys: ExternalServiceKey[]
  ): Promise<ExternalServiceKeys> => {
    const response = await api.instance.put<ActionResult<ExternalServiceKeys>>(
      '/external_services',
      axiosSnakeCaseTransformer({
        services: keys
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  const deleteExternalServices = async (
    serviceToDelete: ExternalServiceName
  ): Promise<ExternalServiceKeys> => {
    const response = await api.instance.delete<
      ActionResult<ExternalServiceKeys>
    >('/external_services', {
      data: {
        services: [serviceToDelete]
      },
      validateStatus: validStatus,
      transformResponse: basicAxiosTransformer
    });

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  };

  return {
    queryExternalServices,
    setExternalServices,
    deleteExternalServices
  };
};
