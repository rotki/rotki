import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { BackendConfiguration } from '@/types/backend';
import { type SettingsUpdate, UserSettingsModel } from '@/types/user';

interface UseSettingApiReturn {
  setSettings: (settings: SettingsUpdate) => Promise<UserSettingsModel>;
  getSettings: () => Promise<UserSettingsModel>;
  getRawSettings: () => Promise<SettingsUpdate>;
  backendSettings: () => Promise<BackendConfiguration>;
  updateBackendConfiguration: (loglevel: string) => Promise<BackendConfiguration>;
}

export function useSettingsApi(): UseSettingApiReturn {
  const setSettings = async (settings: SettingsUpdate): Promise<UserSettingsModel> => {
    const response = await api.put<UserSettingsModel>(
      '/settings',
      { settings },
    );
    return UserSettingsModel.parse(response);
  };

  const getSettings = async (): Promise<UserSettingsModel> => {
    const response = await api.get<UserSettingsModel>('/settings', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return UserSettingsModel.parse(response);
  };

  const getRawSettings = async (): Promise<SettingsUpdate> => api.get<SettingsUpdate>('/settings', {
    validStatuses: VALID_WITH_SESSION_STATUS,
  });

  const backendSettings = async (): Promise<BackendConfiguration> => {
    const response = await api.get<BackendConfiguration>('/settings/configuration');
    return BackendConfiguration.parse(response);
  };

  const updateBackendConfiguration = async (loglevel: string): Promise<BackendConfiguration> => {
    const response = await api.put<BackendConfiguration>(
      '/settings/configuration',
      { loglevel: loglevel.toUpperCase() },
    );
    return BackendConfiguration.parse(response);
  };

  return {
    backendSettings,
    getRawSettings,
    getSettings,
    setSettings,
    updateBackendConfiguration,
  };
}
