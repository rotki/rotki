import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';
import { BackendConfiguration } from '@/types/backend';
import { type SettingsUpdate, UserSettingsModel } from '@/types/user';

interface UseSettingApiReturn {
  setSettings: (settings: SettingsUpdate) => Promise<UserSettingsModel>;
  getSettings: () => Promise<UserSettingsModel>;
  getRawSettings: () => Promise<SettingsUpdate>;
  backendSettings: () => Promise<BackendConfiguration>;
}

export function useSettingsApi(): UseSettingApiReturn {
  const setSettings = async (settings: SettingsUpdate): Promise<UserSettingsModel> => {
    const response = await api.instance.put<ActionResult<UserSettingsModel>>(
      '/settings',
      snakeCaseTransformer({
        settings,
      }),
      {
        validateStatus: validStatus,
      },
    );
    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  };

  const getSettings = async (): Promise<UserSettingsModel> => {
    const response = await api.instance.get<ActionResult<UserSettingsModel>>('/settings', {
      validateStatus: validWithSessionStatus,
    });

    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  };

  const getRawSettings = async (): Promise<SettingsUpdate> => {
    const response = await api.instance.get<ActionResult<SettingsUpdate>>('/settings', {
      validateStatus: validWithSessionStatus,
    });

    return handleResponse(response);
  };

  const backendSettings = async (): Promise<BackendConfiguration> => {
    const response = await api.instance.get<ActionResult<BackendConfiguration>>('/settings/configuration');
    return BackendConfiguration.parse(handleResponse(response));
  };

  return {
    backendSettings,
    getRawSettings,
    getSettings,
    setSettings,
  };
}
