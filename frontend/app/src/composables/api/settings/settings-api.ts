import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { type SettingsUpdate, UserSettingsModel } from '@/types/user';
import { BackendConfiguration } from '@/types/backend';

export const useSettingsApi = () => {
  const setSettings = async (
    settings: SettingsUpdate
  ): Promise<UserSettingsModel> => {
    const response = await api.instance.put<ActionResult<UserSettingsModel>>(
      '/settings',
      axiosSnakeCaseTransformer({
        settings
      }),
      {
        validateStatus: validStatus
      }
    );
    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  };

  const getSettings = async (): Promise<UserSettingsModel> => {
    const response = await api.instance.get<ActionResult<UserSettingsModel>>(
      '/settings',
      {
        validateStatus: validWithSessionStatus
      }
    );

    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  };

  const backendSettings = async (): Promise<BackendConfiguration> => {
    const response = await api.instance.get<ActionResult<BackendConfiguration>>(
      '/settings/configuration'
    );
    return BackendConfiguration.parse(handleResponse(response));
  };

  return {
    setSettings,
    getSettings,
    backendSettings
  };
};
