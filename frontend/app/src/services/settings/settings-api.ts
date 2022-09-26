import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { BackendConfiguration } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { SettingsUpdate, UserSettingsModel } from '@/types/user';

export const useSettingsApi = () => {
  const setSettings = async (
    settings: SettingsUpdate
  ): Promise<UserSettingsModel> => {
    const response = await api.instance.put<ActionResult<UserSettingsModel>>(
      '/settings',
      axiosSnakeCaseTransformer({
        settings: settings
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  };

  const getSettings = async (): Promise<UserSettingsModel> => {
    const response = await api.instance.get<ActionResult<UserSettingsModel>>(
      '/settings',
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  };

  const backendSettings = async (): Promise<BackendConfiguration> => {
    const response = await api.instance.get<ActionResult<BackendConfiguration>>(
      '/settings/configuration',
      {
        transformResponse: basicAxiosTransformer
      }
    );
    return BackendConfiguration.parse(handleResponse(response));
  };

  return {
    setSettings,
    getSettings,
    backendSettings
  };
};
